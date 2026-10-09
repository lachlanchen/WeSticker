import Capacitor
import StoreKit
import UIKit

@objc(WeStickerBillingPlugin)
public class WeStickerBillingPlugin: CAPPlugin, CAPBridgedPlugin {
    public let identifier = "WeStickerBillingPlugin"
    public let jsName = "WeStickerBilling"
    public let pluginMethods: [CAPPluginMethod] = [
        CAPPluginMethod(name: "products", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "purchase", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "restore", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "finish", returnType: CAPPluginReturnPromise),
        CAPPluginMethod(name: "manage", returnType: CAPPluginReturnPromise)
    ]
    private var purchasing = false
    private var updates: Task<Void, Never>?

    override public func load() {
        updates = Task { [weak self] in
            for await update in Transaction.updates {
                guard !Task.isCancelled else { break }
                if case .verified(let tx) = update {
                    // Delivery and finish happen only after server verification.
                    self?.notifyListeners("purchaseUpdated", data: self?.receipt(tx) ?? [:])
                }
            }
        }
    }

    deinit { updates?.cancel() }

    private func receipt(_ tx: Transaction) -> JSObject {
        let body = (try? JSONSerialization.jsonObject(with: tx.jsonRepresentation)) as? [String: Any]
        return ["provider": "apple", "reference": String(tx.originalID),
                "transaction": String(tx.id), "product": tx.productID,
                "environment": body?["environment"] as? String ?? "Production",
                "binding": tx.appAccountToken?.uuidString.lowercased() ?? ""]
    }

    @objc func products(_ call: CAPPluginCall) {
        guard let ids = call.getArray("ids", String.self), !ids.isEmpty,
              ids.count <= 3, ids.allSatisfy({ $0.hasPrefix("art.lazying.westicker.") }) else {
            call.reject("Invalid WeSticker catalog"); return
        }
        Task {
            do {
                let products = try await Product.products(for: ids)
                call.resolve(["products": products.filter { $0.type == .autoRenewable }.map {
                    ["id": $0.id, "name": $0.displayName, "price": $0.displayPrice]
                }])
            } catch { call.reject("Store prices could not be loaded") }
        }
    }

    @objc func purchase(_ call: CAPPluginCall) {
        guard let id = call.getString("product"), id.hasPrefix("art.lazying.westicker."),
              let owner = call.getString("binding"), let account = UUID(uuidString: owner) else {
            call.reject("Missing purchase account"); return
        }
        Task { @MainActor in
            guard !self.purchasing else { call.reject("A purchase is already open"); return }
            self.purchasing = true
            defer { self.purchasing = false }
            do {
                for await result in Transaction.unfinished {
                    if case .verified(let tx) = result, tx.productID.hasPrefix("art.lazying.westicker.") {
                        call.reject("Restore the unfinished purchase before paying again"); return
                    }
                }
                for await result in Transaction.currentEntitlements {
                    if case .verified(let tx) = result, tx.productID.hasPrefix("art.lazying.westicker.") {
                        call.reject("An existing subscription needs Restore or Manage"); return
                    }
                }
                guard let product = try await Product.products(for: [id]).first,
                      product.type == .autoRenewable else {
                    call.reject("This subscription is unavailable"); return
                }
                let result = try await product.purchase(options: [.appAccountToken(account)])
                switch result {
                case .success(let proof):
                    guard case .verified(let tx) = proof, tx.appAccountToken == account else {
                        call.reject("Store verification is pending. Use Restore; do not pay again"); return
                    }
                    call.resolve(["state": "purchased", "receipts": [self.receipt(tx)]])
                case .pending: call.resolve(["state": "pending", "receipts": []])
                case .userCancelled: call.resolve(["state": "cancelled", "receipts": []])
                @unknown default: call.reject("Unknown store result. Use Restore; do not pay again")
                }
            } catch { call.reject("Purchase did not complete. Use Restore before another attempt") }
        }
    }

    @objc func restore(_ call: CAPPluginCall) {
        Task {
            do {
                if call.getBool("sync") == true { try await AppStore.sync() }
                var found: [String: JSObject] = [:]
                for await proof in Transaction.currentEntitlements {
                    if case .verified(let tx) = proof, tx.productID.hasPrefix("art.lazying.westicker.") {
                        found[String(tx.id)] = receipt(tx)
                    }
                }
                for await proof in Transaction.unfinished {
                    if case .verified(let tx) = proof, tx.productID.hasPrefix("art.lazying.westicker.") {
                        found[String(tx.id)] = receipt(tx)
                    }
                }
                call.resolve(["receipts": Array(found.values)])
            } catch { call.reject("Store restore is unavailable. Existing purchases are preserved") }
        }
    }

    @objc func finish(_ call: CAPPluginCall) {
        guard let id = call.getString("transaction"), let owner = call.getString("binding") else {
            call.reject("Missing transaction"); return
        }
        Task {
            for await proof in Transaction.unfinished {
                if case .verified(let tx) = proof, String(tx.id) == id,
                   tx.appAccountToken?.uuidString.lowercased() == owner,
                   tx.productID.hasPrefix("art.lazying.westicker.") {
                    await tx.finish()
                }
            }
            call.resolve()
        }
    }

    @objc func manage(_ call: CAPPluginCall) {
        Task { @MainActor in
            guard let url = URL(string: "https://apps.apple.com/account/subscriptions") else { return }
            UIApplication.shared.open(url)
            call.resolve()
        }
    }
}

class WeStickerViewController: CAPBridgeViewController {
    override func capacitorDidLoad() {
        bridge?.registerPluginInstance(WeStickerBillingPlugin())
    }
}
