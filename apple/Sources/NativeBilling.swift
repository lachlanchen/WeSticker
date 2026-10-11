import SwiftUI
import StoreKit
import Security
#if os(iOS)
import UIKit
#else
import AppKit
#endif

private enum BillingFailure: LocalizedError {
    case stale, unavailable, ownership, unresolved, storage
    var errorDescription: String? {
        switch self {
        case .stale: return "Your account changed. Return to the purchase account and restore."
        case .unavailable: return "Store verification is unavailable. Restore before paying again."
        case .ownership: return "This purchase belongs to another WeSticker account. Sign in to its original account."
        case .unresolved: return "An existing or pending purchase needs Restore or Manage before another purchase."
        case .storage: return "Purchase recovery could not be saved. No new purchase was started."
        }
    }
}

private enum BillingVault {
    static func query(_ key: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: "art.lazying.westicker.billing", kSecAttrAccount as String: key]
    }
    static func read(_ key: String) throws -> NativeBillingJournal {
        var q = query(key); q[kSecReturnData as String] = true
        var value: CFTypeRef?
        let status = SecItemCopyMatching(q as CFDictionary, &value)
        if status == errSecItemNotFound { return NativeBillingJournal() }
        guard status == errSecSuccess, let data = value as? Data else { throw BillingFailure.storage }
        return try JSONDecoder().decode(NativeBillingJournal.self, from: data)
    }
    static func write(_ value: NativeBillingJournal, key: String) throws {
        let data = try JSONEncoder().encode(value), q = query(key)
        let status = SecItemUpdate(q as CFDictionary, [kSecValueData as String: data] as CFDictionary)
        if status == errSecItemNotFound {
            var entry = q; entry[kSecValueData as String] = data
            entry[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            guard SecItemAdd(entry as CFDictionary, nil) == errSecSuccess else { throw BillingFailure.storage }
        } else if status != errSecSuccess { throw BillingFailure.storage }
    }
}

@MainActor final class NativeBillingStore: ObservableObject {
    @Published private(set) var products: [Product] = []
    @Published private(set) var tiers: [String: String] = [:]
    @Published private(set) var salesEnabled = false
    @Published private(set) var busy = false
    @Published private(set) var presenting = false
    @Published private(set) var ready = false
    @Published private(set) var blocked = true
    @Published private(set) var message: String?
    @Published private(set) var account = ""
    @Published private(set) var plan = "free"
    @Published private(set) var credits = 0
    @Published private(set) var attempt: NativeBillingAttempt?
    private weak var cloud: CloudStudioStore?
    private var session: NativeBillingSession?
    private var binding = ""
    private var journal = NativeBillingJournal()
    private var updates: Task<Void, Never>?
    private var generation = UUID()
    private var operation: UUID?
    private let network = URLSession(configuration: .ephemeral)

    func attach(_ cloud: CloudStudioStore) {
        self.cloud = cloud
        if updates == nil {
            updates = Task { [weak self] in
                for await _ in StoreKit.Transaction.updates {
                    guard !Task.isCancelled else { return }
                    // Unfinished transactions remain recoverable if another operation is busy.
                    self?.restore()
                }
            }
        }
        guard !(session?.sameAccountSession(as: cloud.billingSession) ?? (cloud.billingSession == nil)) else { return }
        generation = UUID(); session = cloud.billingSession; operation = nil
        products = []; tiers = [:]; ready = false; busy = false; blocked = true
        binding = ""; account = ""; plan = "free"; credits = 0; message = nil
        journal = NativeBillingJournal(); attempt = nil; salesEnabled = false
        restore()
    }
    deinit { updates?.cancel() }

    private func check(_ s: NativeBillingSession, _ g: UUID) throws {
        guard g == generation, s.sameAccountSession(as: session), s.sameAccountSession(as: cloud?.billingSession) else { throw BillingFailure.stale }
    }
    private func api(_ path: String, _ body: [String: Any]? = nil, _ s: NativeBillingSession, _ g: UUID) async throws -> [String: Any] {
        try check(s, g)
        var req = URLRequest(url: URL(string: s.origin + path)!)
        req.httpMethod = body == nil ? "GET" : "POST"; req.timeoutInterval = 45
        req.setValue(s.origin, forHTTPHeaderField: "Origin")
        req.setValue("Bearer " + s.token, forHTTPHeaderField: "Authorization")
        req.setValue(s.csrf, forHTTPHeaderField: "X-CSRF-Token")
        if let body { req.httpBody = try JSONSerialization.data(withJSONObject: body); req.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        let (data, response) = try await network.data(for: req)
        try check(s, g)
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode),
              let value = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw BillingFailure.unavailable }
        return value
    }
    private func persist(_ s: NativeBillingSession, _ g: UUID) throws {
        try check(s, g)
        try BillingVault.write(journal, key: s.origin + ":" + binding)
        attempt = journal.attempt
    }
    private func run(_ action: @escaping (NativeBillingSession, UUID) async throws -> Void) {
        guard !busy, let s = session else { return }
        let g = generation, id = UUID(); operation = id; busy = true; message = nil
        Task {
            defer { if operation == id { busy = false; operation = nil } }
            do { try check(s, g); try await action(s, g) }
            catch { if (try? check(s, g)) != nil { blocked = true; message = (error as? BillingFailure)?.localizedDescription ?? BillingFailure.unavailable.localizedDescription } }
        }
    }
    private func loadAccount(_ s: NativeBillingSession, _ g: UUID) async throws -> Bool {
        let result = try await api("/api/bootstrap", nil, s, g)
        guard let user = result["user"] as? [String: Any] else { throw BillingFailure.stale }
        account = user["name"] as? String ?? "WeSticker account"
        plan = user["plan"] as? String ?? "free"; credits = user["credits"] as? Int ?? 0
        return (user["expires"] as? Double ?? 0) > Date().timeIntervalSince1970
    }
    private func loadCatalog(_ s: NativeBillingSession, _ g: UUID) async throws {
        let result = try await api("/api/billing/native/catalog", nil, s, g)
        guard let providers = result["providers"] as? [String: Any], let catalog = providers["apple"] as? [String: Any],
              let owner = catalog["binding"] as? String, UUID(uuidString: owner) != nil,
              let ids = catalog["products"] as? [String: String] else { throw BillingFailure.unavailable }
        binding = owner.lowercased(); tiers = ids; salesEnabled = catalog["purchase_enabled"] as? Bool == true
        journal = try BillingVault.read(s.origin + ":" + binding); attempt = journal.attempt
    }
    private func transactions(_ s: NativeBillingSession, _ g: UUID) async throws -> [StoreKit.Transaction] {
        var found: [UInt64: StoreKit.Transaction] = [:]
        for await proof in StoreKit.Transaction.currentEntitlements {
            try check(s, g)
            switch proof {
            case .verified(let tx): if tx.productType == .autoRenewable { found[tx.id] = tx }
            case .unverified: throw BillingFailure.unresolved
            }
        }
        for await proof in StoreKit.Transaction.unfinished {
            try check(s, g)
            switch proof {
            case .verified(let tx): if tx.productType == .autoRenewable { found[tx.id] = tx }
            case .unverified: throw BillingFailure.unresolved
            }
        }
        return Array(found.values)
    }
    private func deliver(_ tx: StoreKit.Transaction, _ s: NativeBillingSession, _ g: UUID) async throws {
        try check(s, g)
        guard tx.appAccountToken?.uuidString.lowercased() == binding else { throw BillingFailure.ownership }
        let value = try JSONSerialization.jsonObject(with: tx.jsonRepresentation) as? [String: Any]
        guard let environment = value?["environment"] as? String, ["Production", "Sandbox"].contains(environment) else { throw BillingFailure.unavailable }
        let receipt = NativeBillingReceipt(reference: String(tx.originalID), environment: environment, product: tx.productID)
        journal.receipts[environment + ":" + receipt.reference] = receipt
        try persist(s, g)
        try await verify(receipt, s, g)
        try check(s, g)
        await tx.finish()
        try check(s, g)
    }
    private func verify(_ receipt: NativeBillingReceipt, _ s: NativeBillingSession, _ g: UUID) async throws {
        let result = try await api("/api/billing/native/verify", ["provider": "apple", "reference": receipt.reference, "environment": receipt.environment], s, g)
        guard result["verified"] as? Bool == true else { throw BillingFailure.unavailable }
        journal.attempt = NativeBillingRecovery.afterVerification(journal.attempt, product: receipt.product, verified: true, active: result["active"] as? Bool == true)
        try persist(s, g)
    }
    private func outcome(_ s: NativeBillingSession, _ g: UUID) async throws {
        guard let a = journal.attempt, a.reportable else { return }
        _ = try await api("/api/billing/native/outcome", ["attempt": a.id, "state": a.phase], s, g)
        if a.phase == "cancelled" { journal.attempt = nil; try persist(s, g) }
    }
    func restore(sync: Bool = false) {
        run { [self] s, g in
            ready = false; blocked = true
            try await loadCatalog(s, g)
            _ = try await loadAccount(s, g)
            let metadata = (try? await Product.products(for: Array(tiers.keys))) ?? []
            try check(s, g)
            products = metadata.filter { $0.type == .autoRenewable }.sorted { $0.price < $1.price }
            if sync { try await AppStore.sync(); try check(s, g) }
            try await outcome(s, g)
            let found = try await transactions(s, g)
            for tx in found { try await deliver(tx, s, g) }
            let handled = Set(found.map { String($0.originalID) })
            for receipt in Array(journal.receipts.values) where !handled.contains(receipt.reference) { try await verify(receipt, s, g) }
            let paidThrough = try await loadAccount(s, g)
            blocked = presenting || !NativeBillingRecovery.mayPurchase(enabled: true, ready: true, paidThrough: paidThrough, storeOwned: !found.isEmpty, attempt: journal.attempt)
            ready = true
            message = journal.attempt != nil ? "A purchase is awaiting recovery. No additional payment will be started automatically." :
                (products.count < tiers.count ? "Some App Store plans are unavailable. Restore and Manage remain available." : nil)
        }
    }
    func purchase(_ product: Product) {
        guard ready, salesEnabled, !blocked, !presenting, tiers[product.id] != nil else { return }
        startPurchase(product, resuming: false)
    }
    func resumePreparation() {
        guard ready, salesEnabled, !presenting, let a = attempt, a.canResume, let product = products.first(where: { $0.id == a.product }) else { return }
        startPurchase(product, resuming: true)
    }
    private func startPurchase(_ product: Product, resuming: Bool) {
        run { [self] s, g in
            let existing = try await transactions(s, g)
            let paidThrough = try await loadAccount(s, g)
            guard existing.isEmpty, !paidThrough else { throw BillingFailure.unresolved }
            try await loadCatalog(s, g)
            guard salesEnabled, tiers[product.id] != nil, let owner = UUID(uuidString: binding) else { throw BillingFailure.unavailable }
            if resuming {
                guard journal.attempt?.phase == "prepared", journal.attempt?.product == product.id else { throw BillingFailure.unresolved }
            } else {
                guard journal.attempt == nil else { throw BillingFailure.unresolved }
                journal.attempt = NativeBillingAttempt(product: product.id)
            }
            try persist(s, g); blocked = true
            let prepared = try await api("/api/billing/native/prepare", ["provider": "apple", "product": product.id, "attempt": journal.attempt!.id], s, g)
            guard (prepared["binding"] as? String)?.lowercased() == binding, prepared["attempt"] as? String == journal.attempt?.id else { throw BillingFailure.ownership }
            #if os(iOS)
            guard let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first(where: { $0.activationState == .foregroundActive && $0.windows.contains(where: \.isKeyWindow) }) else { throw BillingFailure.unavailable }
            #else
            guard NSApp.isActive, let window = NSApp.keyWindow else { throw BillingFailure.unavailable }
            #endif
            journal.attempt?.phase = "presented"; try persist(s, g)
            presenting = true
            defer { presenting = false }
            let result: Product.PurchaseResult
            #if os(iOS)
            if #available(iOS 17.0, *) { result = try await product.purchase(confirmIn: scene, options: [.appAccountToken(owner)]) }
            else { result = try await product.purchase(options: [.appAccountToken(owner)]) }
            #else
            if #available(macOS 15.2, *) { result = try await product.purchase(confirmIn: window, options: [.appAccountToken(owner)]) }
            else { result = try await product.purchase(options: [.appAccountToken(owner)]) }
            #endif
            try check(s, g)
            switch result {
            case .success(let proof):
                guard case .verified(let tx) = proof else { throw BillingFailure.unresolved }
                try await deliver(tx, s, g)
                _ = try await loadAccount(s, g)
                message = "Purchase verified. Your account has been refreshed."
            case .pending:
                journal.attempt?.phase = "pending"; try persist(s, g); try await outcome(s, g)
                message = "Payment is pending. Restore after approval; do not pay again."
            case .userCancelled:
                journal.attempt?.phase = "cancelled"; try persist(s, g); try await outcome(s, g)
                blocked = false; message = "Purchase cancelled."
            @unknown default: throw BillingFailure.unresolved
            }
        }
    }
    func manage() {
        #if os(iOS)
        guard let scene = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).first(where: { $0.activationState == .foregroundActive && $0.windows.contains(where: \.isKeyWindow) }) else { return }
        Task { do { try await AppStore.showManageSubscriptions(in: scene); restore() } catch { message = "App Store subscription management could not be opened." } }
        #else
        NSWorkspace.shared.open(URL(string: "https://apps.apple.com/account/subscriptions")!)
        #endif
    }
}

struct NativeBillingAccountView: View {
    @ObservedObject var cloud: CloudStudioStore
    @ObservedObject var billing: NativeBillingStore
    var body: some View {
        NavigationStack {
            Form {
                Section {
                    if cloud.busy { ProgressView() }
                    if let error = cloud.error { Text(error).font(.caption).foregroundStyle(.red) }
                    if cloud.signedIn {
                        Text(billing.account.isEmpty ? "Signed in" : billing.account)
                        Text("\(billing.plan.capitalized) - \(billing.credits) credits")
                        Button(role: .destructive) { cloud.perform { try await cloud.signOut() } } label: { Label("Sign out", systemImage: "rectangle.portrait.and.arrow.right") }
                    }
                }
                if cloud.signedIn {
                    Section("App Store Plans") {
                        if billing.busy { ProgressView() }
                        if let message = billing.message { Text(message).foregroundStyle(.secondary) }
                        if !billing.salesEnabled { Text("New purchases are not enabled. Restore and Manage remain available.") }
                        if billing.tiers.isEmpty { Text("No App Store plans are configured for this service.") }
                        ForEach(billing.products, id: \.id) { product in
                            VStack(alignment: .leading, spacing: 8) {
                                Text(product.displayName).font(.headline)
                                Text(product.description).font(.subheadline)
                                Text(product.displayPrice + period(product))
                                Button { billing.purchase(product) } label: { Label("Subscribe", systemImage: "cart") }
                                    .disabled(billing.busy || billing.presenting || !billing.ready || !billing.salesEnabled || billing.blocked)
                            }.padding(.vertical, 4)
                        }
                        if billing.attempt?.phase == "prepared" {
                            Button("Continue prepared purchase") { billing.resumePreparation() }.disabled(billing.busy || billing.presenting || !billing.ready || !billing.salesEnabled)
                        }
                        Button { billing.restore() } label: { Label("Restore purchases", systemImage: "arrow.clockwise") }.disabled(billing.busy)
                        Button("Find missing App Store purchases") { billing.restore(sync: true) }.disabled(billing.busy)
                    }
                }
                Section {
                    Button { billing.manage() } label: { Label("Manage App Store subscriptions", systemImage: "creditcard") }
                    if let base = try? cloud.validatedOrigin() {
                        Link("Terms", destination: URL(string: base + "/terms.html")!)
                        Link("Privacy", destination: URL(string: base + "/privacy.html")!)
                    }
                    Link("Apple Standard EULA", destination: URL(string: "https://www.apple.com/legal/internet-services/itunes/dev/stdeula/")!)
                    Text("Subscriptions renew automatically until cancelled in your App Store account.").font(.footnote).foregroundStyle(.secondary)
                }
            }.compactStudioHeader("Account")
        }
    }
    private func period(_ product: Product) -> String {
        guard let p = product.subscription?.subscriptionPeriod else { return "" }
        let unit: String
        switch p.unit { case .day: unit = "day"; case .week: unit = "week"; case .month: unit = "month"; case .year: unit = "year"; @unknown default: unit = "period" }
        return " / \(p.value) \(unit)\(p.value == 1 ? "" : "s")"
    }
}
