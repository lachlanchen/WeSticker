import Foundation

struct NativeBillingSession: Equatable {
    let origin: String
    let token: String
    let csrf: String
    func sameAccountSession(as other: Self?) -> Bool {
        other?.origin == origin && other?.token == token
    }
}

struct NativeBillingAttempt: Codable, Equatable {
    var id: String = UUID().uuidString.lowercased()
    var product: String
    // Only a request that has never presented a sheet may be resumed.
    var phase = "prepared"
    var canResume: Bool { phase == "prepared" }
    var reportable: Bool { ["cancelled", "pending"].contains(phase) }
}
struct NativeBillingReceipt: Codable {
    let reference: String
    let environment: String
    let product: String
}
struct NativeBillingJournal: Codable {
    var attempt: NativeBillingAttempt?
    var receipts: [String: NativeBillingReceipt] = [:]
}
enum NativeBillingRecovery {
    static func mayPurchase(enabled: Bool, ready: Bool, paidThrough: Bool, storeOwned: Bool, attempt: NativeBillingAttempt?) -> Bool {
        enabled && ready && !paidThrough && !storeOwned && attempt == nil
    }
    static func afterVerification(_ attempt: NativeBillingAttempt?, product: String, verified: Bool, active: Bool) -> NativeBillingAttempt? {
        verified && active && attempt?.product == product ? nil : attempt
    }
}
