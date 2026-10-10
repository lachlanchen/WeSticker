package art.lazying.westicker;

import android.content.Intent;
import android.net.Uri;
import android.os.Handler;
import android.os.Looper;
import com.android.billingclient.api.*;
import com.getcapacitor.*;
import com.getcapacitor.annotation.CapacitorPlugin;
import java.util.*;
import java.util.concurrent.atomic.AtomicBoolean;

@CapacitorPlugin(name = "WeStickerBilling")
public class WeStickerBillingPlugin extends Plugin {
    private BillingClient client;
    private PluginCall activePurchase;

    private synchronized void reject(PluginCall call, String message) {
        if (activePurchase == call) activePurchase = null;
        call.reject(message);
    }

    @Override public void load() {
        client = BillingClient.newBuilder(getContext())
            .setListener((result, purchases) -> {
                PluginCall call = activePurchase;
                activePurchase = null;
                if (result.getResponseCode() == BillingClient.BillingResponseCode.USER_CANCELED) {
                    if (call != null) call.resolve(new JSObject().put("state", "cancelled").put("receipts", new JSArray()));
                } else if (result.getResponseCode() == BillingClient.BillingResponseCode.OK && purchases != null) {
                    boolean pending = purchases.stream().anyMatch(p -> p.getPurchaseState() == Purchase.PurchaseState.PENDING);
                    JSObject response = new JSObject().put("state", pending ? "pending" : "purchased").put("receipts", receipts(purchases));
                    if (call != null) call.resolve(response);
                    else notifyListeners("purchaseUpdated", response);
                } else if (call != null) reject(call, "Store result uncertain. Restore before another purchase");
            })
            .enablePendingPurchases(PendingPurchasesParams.newBuilder().enableOneTimeProducts().build())
            .enableAutoServiceReconnection().build();
    }

    private void ready(PluginCall call, Runnable action) {
        getActivity().runOnUiThread(() -> {
            if (client.isReady()) { action.run(); return; }
            AtomicBoolean finished = new AtomicBoolean();
            Handler handler = new Handler(Looper.getMainLooper());
            Runnable timeout = () -> {
                if (finished.compareAndSet(false, true)) reject(call, "Google Play connection timed out. Restore before another purchase");
            };
            handler.postDelayed(timeout, 20000);
            client.startConnection(new BillingClientStateListener() {
                public void onBillingSetupFinished(BillingResult result) {
                    if (!finished.compareAndSet(false, true)) return;
                    handler.removeCallbacks(timeout);
                    if (result.getResponseCode() == BillingClient.BillingResponseCode.OK) action.run();
                    else reject(call, "Google Play is unavailable");
                }
                public void onBillingServiceDisconnected() { }
            });
        });
    }

    private JSArray receipts(List<Purchase> purchases) {
        JSArray result = new JSArray();
        for (Purchase purchase : purchases) {
            if (purchase.getPurchaseState() != Purchase.PurchaseState.PURCHASED) continue;
            if (purchase.getProducts().stream().noneMatch(id -> id.startsWith("westicker_"))) continue;
            AccountIdentifiers owner = purchase.getAccountIdentifiers();
            result.put(new JSObject().put("provider", "google").put("token", purchase.getPurchaseToken())
                .put("binding", owner == null ? "" : owner.getObfuscatedAccountId()));
        }
        return result;
    }

    private ProductDetails.SubscriptionOfferDetails offer(ProductDetails product) {
        List<ProductDetails.SubscriptionOfferDetails> offers = product.getSubscriptionOfferDetails();
        if (offers == null) return null;
        for (ProductDetails.SubscriptionOfferDetails offer : offers) {
            List<ProductDetails.PricingPhase> phases = offer.getPricingPhases().getPricingPhaseList();
            if (offer.getBasePlanId().equals("monthly") && offer.getOfferId() == null && phases.size() == 1
                && phases.get(0).getRecurrenceMode() == ProductDetails.RecurrenceMode.INFINITE_RECURRING) return offer;
        }
        return null;
    }

    private void details(List<String> ids, PluginCall call, java.util.function.Consumer<List<ProductDetails>> next) {
        List<QueryProductDetailsParams.Product> products = new ArrayList<>();
        for (String id : ids) products.add(QueryProductDetailsParams.Product.newBuilder()
            .setProductId(id).setProductType(BillingClient.ProductType.SUBS).build());
        client.queryProductDetailsAsync(QueryProductDetailsParams.newBuilder().setProductList(products).build(), (result, response) -> {
            if (result.getResponseCode() != BillingClient.BillingResponseCode.OK) reject(call, "Store prices unavailable");
            else next.accept(response.getProductDetailsList());
        });
    }

    @PluginMethod public void products(PluginCall call) {
        List<String> ids;
        try { ids = call.getArray("ids").toList(); }
        catch (Exception e) { call.reject("Missing catalog"); return; }
        if (ids.isEmpty() || ids.size() > 3 || ids.stream().anyMatch(x -> !x.startsWith("westicker_"))) {
            call.reject("Invalid catalog"); return;
        }
        ready(call, () -> details(ids, call, list -> {
            JSArray values = new JSArray();
            for (ProductDetails product : list) {
                ProductDetails.SubscriptionOfferDetails offer = offer(product);
                if (offer != null) values.put(new JSObject().put("id", product.getProductId())
                    .put("name", product.getName()).put("price", offer.getPricingPhases().getPricingPhaseList().get(0).getFormattedPrice()));
            }
            call.resolve(new JSObject().put("products", values));
        }));
    }

    @PluginMethod public void purchase(PluginCall call) {
        String id = call.getString("product"), owner = call.getString("binding");
        if (id == null || !id.startsWith("westicker_") || owner == null || !owner.matches("[a-f0-9]{64}")) {
            call.reject("Invalid purchase account"); return;
        }
        synchronized (this) {
            if (activePurchase != null) { call.reject("A purchase is already open"); return; }
            activePurchase = call;
        }
        ready(call, () -> {
            client.queryPurchasesAsync(QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.SUBS).build(), (result, existing) -> {
                if (result.getResponseCode() != BillingClient.BillingResponseCode.OK || !existing.isEmpty()) {
                    reject(call, "Restore or manage the existing purchase first"); return;
                }
                details(List.of(id), call, products -> {
                    if (products.size() != 1 || offer(products.get(0)) == null) {
                        reject(call, "Subscription unavailable"); return;
                    }
                    ProductDetails product = products.get(0);
                    BillingFlowParams params = BillingFlowParams.newBuilder().setObfuscatedAccountId(owner)
                        .setProductDetailsParamsList(List.of(BillingFlowParams.ProductDetailsParams.newBuilder()
                            .setProductDetails(product).setOfferToken(offer(product).getOfferToken()).build())).build();
                    getActivity().runOnUiThread(() -> {
                        BillingResult opened = client.launchBillingFlow(getActivity(), params);
                        if (opened.getResponseCode() != BillingClient.BillingResponseCode.OK) {
                            reject(call, "Purchase could not open. Restore before another attempt");
                        }
                    });
                });
            });
        });
    }

    @PluginMethod public void restore(PluginCall call) {
        ready(call, () -> client.queryPurchasesAsync(QueryPurchasesParams.newBuilder()
            .setProductType(BillingClient.ProductType.SUBS).build(), (result, list) -> {
                if (result.getResponseCode() != BillingClient.BillingResponseCode.OK) call.reject("Restore unavailable");
                else call.resolve(new JSObject().put("receipts", receipts(list)));
            }));
    }

    @PluginMethod public void finish(PluginCall call) {
        // Play acknowledgement is performed by the server after durable delivery.
        call.resolve();
    }

    @PluginMethod public void manage(PluginCall call) {
        getActivity().startActivity(new Intent(Intent.ACTION_VIEW,
            Uri.parse("https://play.google.com/store/account/subscriptions?package=art.lazying.westicker")));
        call.resolve();
    }

    @Override protected void handleOnDestroy() {
        if (client != null) client.endConnection();
    }
}
