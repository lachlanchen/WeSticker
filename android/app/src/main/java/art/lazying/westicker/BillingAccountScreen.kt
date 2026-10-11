package art.lazying.westicker

import android.app.Activity
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun BillingAccountScreen(cloud: CloudStudioStore, billing: NativeBillingStore) {
    val activity = LocalContext.current as? Activity
    val scope = rememberCoroutineScope()
    Scaffold(topBar = { TopAppBar(title = { Text("Account") }) }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Text("WeSticker Account", style = MaterialTheme.typography.titleLarge)
            if (cloud.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            cloud.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            if (cloud.signedIn) {
                Text(billing.account.ifBlank { "Signed in" })
                Text("${billing.plan.replaceFirstChar { it.uppercase() }} - ${billing.credits} credits")
                TextButton(onClick = { scope.launch { cloud.run { cloud.signOut() } } }, enabled = !cloud.busy) { Icon(Icons.Outlined.Logout, null); Text("Sign out", Modifier.padding(start = 8.dp)) }
                HorizontalDivider()
                Text("Google Play Plans", style = MaterialTheme.typography.titleLarge)
                if (billing.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
                billing.message?.let { Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                if (!billing.salesEnabled) Text("New purchases are not enabled. Restore and Manage remain available.")
                if (billing.configuredCount == 0) Text("No Play Store plans are configured for this service.")
                billing.plans.forEach { plan ->
                    Text(plan.details.name, style = MaterialTheme.typography.titleMedium)
                    Text(plan.details.description)
                    Text("${plan.price} / month")
                    Button(onClick = { activity?.let { billing.purchase(it, plan) } }, enabled = activity != null && billing.ready && !billing.busy && billing.salesEnabled && !billing.blocked) {
                        Icon(Icons.Outlined.ShoppingCart, null); Text("Subscribe", Modifier.padding(start = 8.dp))
                    }
                    HorizontalDivider()
                }
                billing.attempt?.takeIf { it.canResume }?.let { attempt ->
                    val plan = billing.plans.find { it.id == attempt.product }
                    TextButton(onClick = { if (activity != null && plan != null) billing.purchase(activity, plan, resume = true) }, enabled = plan != null && billing.ready && !billing.busy && billing.salesEnabled) { Text("Continue prepared purchase") }
                }
                OutlinedButton(onClick = { billing.restore() }, enabled = !billing.busy) { Icon(Icons.Outlined.Refresh, null); Text("Restore purchases", Modifier.padding(start = 8.dp)) }
            }
            OutlinedButton(onClick = { activity?.let { billing.manage(it) } }, enabled = activity != null) { Icon(Icons.Outlined.CreditCard, null); Text("Manage Play subscriptions", Modifier.padding(start = 8.dp)) }
            listOf("Terms" to "/terms.html", "Privacy" to "/privacy.html").forEach { (label, path) ->
                TextButton(onClick = { activity?.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(cloud.base() + path))) }) { Text(label) }
            }
            Text("Subscriptions renew automatically until cancelled in your Play Store account.", style = MaterialTheme.typography.bodySmall)
        }
    }
}
