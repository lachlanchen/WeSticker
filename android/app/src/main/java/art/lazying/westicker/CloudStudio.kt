package art.lazying.westicker

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.ImageDecoder
import android.os.Build
import android.net.Uri
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import coil.ImageLoader
import coil.compose.AsyncImage
import coil.request.ImageRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.nio.ByteBuffer
import java.security.KeyStore
import java.security.MessageDigest
import java.util.UUID
import java.util.Locale
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

private fun JSONArray.objects() = (0 until length()).map { getJSONObject(it) }
private fun newStudioID() = UUID.randomUUID().toString().replace("-", "")

class CloudStudioStore(val context: Context) {
    private val prefs = context.getSharedPreferences("cloud-studio", Context.MODE_PRIVATE)
    private var originValue by mutableStateOf(prefs.getString("origin", "https://westicker.lazying.art") ?: "https://westicker.lazying.art")
    var origin: String
        get() = originValue
        set(value) { if (value != originValue) { originValue = value; clearGuestChat() } }
    var workspace by mutableStateOf<JSONObject?>(null)
    var current by mutableStateOf<JSONObject?>(null)
    var rows by mutableStateOf<List<JSONObject>>(emptyList())
    var messages by mutableStateOf<List<JSONObject>>(emptyList())
    var selected by mutableStateOf<Set<String>>(emptySet())
    var refs by mutableStateOf<List<String>>(emptyList())
    var quote by mutableStateOf<JSONObject?>(null)
    private var signedInValue by mutableStateOf(false)
    var signedIn: Boolean
        get() = signedInValue
        set(value) { if (value != signedInValue) { signedInValue = value; clearGuestChat() } }
    private var needsConsentValue by mutableStateOf(false)
    var needsConsent: Boolean
        get() = needsConsentValue
        set(value) { if (value != needsConsentValue) { needsConsentValue = value; clearGuestChat() } }
    var capabilities by mutableStateOf(JSONObject())
    var busy by mutableStateOf(false)
    var dirty by mutableStateOf(false)
    var error by mutableStateOf<String?>(null)
    var creating by mutableStateOf(false)
    var sending by mutableStateOf(false)
    var character by mutableStateOf("")
    var guestMessages by mutableStateOf<List<GuestChatExchange>>(emptyList())
    var guestDraft by mutableStateOf("")
    var guestSending by mutableStateOf(false)
    var guestError by mutableStateOf<String?>(null)
    private var guestGeneration = 0
    private var guestJob: Job? = null
    private var csrf = ""
    private var linkedOrigin = ""
    private var link: Pair<String, String>? = null
    val usesGuestChat get() = !signedIn || needsConsent
    fun clearGuestChat() {
        guestGeneration += 1
        guestJob?.cancel(); guestJob = null
        guestMessages = emptyList(); guestDraft = ""; guestSending = false; guestError = null
    }
    fun sendGuestChat(scope: CoroutineScope) {
        if (!usesGuestChat || guestSending) return
        try {
            val origin = base()
            val text = guestDraft.trim()
            val request = GuestChatClient.request(origin, text, guestMessages, Locale.getDefault().language)
            val generation = guestGeneration
            val id = UUID.randomUUID().toString()
            guestMessages = guestMessages + GuestChatExchange(id, text)
            guestDraft = ""; guestError = null; guestSending = true
            guestJob = scope.launch {
                fun current() = generation == guestGeneration && usesGuestChat && runCatching { base() == origin }.getOrDefault(false)
                try {
                    val reply = GuestChatClient.send(request)
                    if (current()) guestMessages = guestMessages.map { if (it.id == id) it.copy(reply = reply) else it }
                } catch (e: Exception) {
                    if (current()) guestMessages = guestMessages.map {
                        if (it.id == id) it.copy(failure = if (e is CancellationException) "Reply cancelled." else e.message ?: "Chat is unavailable.") else it
                    }
                    if (e is CancellationException) throw e
                } finally {
                    if (generation == guestGeneration) { guestSending = false; guestJob = null }
                }
            }
        } catch (e: Exception) { guestError = e.message ?: "Check the service address." }
    }
    fun billingSession(): BillingSession? {
        if (!signedIn) return null
        return runCatching {
            val auth = token()
            if (auth.isBlank()) null else BillingSession(base(), auth, csrf)
        }.getOrNull()
    }
    fun billingRead(session: BillingSession, owner: String): String {
        check(session.sameAccountSession(billingSession())) { "Account changed" }
        return readSecret("billing:$owner:", strict = true)
    }
    fun billingWrite(session: BillingSession, owner: String, value: String) {
        check(session.sameAccountSession(billingSession())) { "Account changed" }
        saveSecret("billing:$owner:", value)
        check(readSecret("billing:$owner:", strict = true) == value) { "Purchase recovery could not be saved" }
    }
    fun base(): String {
        val value = origin.trim().trimEnd('/')
        val url = URL(value)
        require(url.protocol == "https" || url.protocol == "http" && url.host in listOf("127.0.0.1", "localhost", "10.0.2.2")) { "Use an HTTPS creator-service origin." }
        require(url.path.isEmpty() && url.query == null && url.userInfo == null && url.ref == null) { "Use only the service origin, without a path." }
        return value
    }
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val alias = "westicker-studio-session"
        if (!store.containsAlias(alias)) KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build()); generateKey()
        }
        return store.getKey(alias, null) as SecretKey
    }
    fun token(): String = readSecret("token:")
    private fun readSecret(slot: String, strict: Boolean = false): String {
        val saved = prefs.getString(slot + base(), null) ?: return ""
        return try { val parts = saved.split('.'); val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(parts[0], Base64.NO_WRAP)))
            String(cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)), Charsets.UTF_8)
        } catch (e: Exception) { if (strict) throw IllegalStateException("Purchase recovery could not be read", e); "" }
    }
    private fun saveToken(value: String) = saveSecret("token:", value)
    private fun saveSecret(slot: String, value: String) {
        if(value.isEmpty()) { prefs.edit().remove(slot + base()).commit(); return }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding"); cipher.init(Cipher.ENCRYPT_MODE, key())
        val encrypted = cipher.doFinal(value.toByteArray())
        prefs.edit().putString(slot + base(), Base64.encodeToString(cipher.iv, Base64.NO_WRAP) + "." + Base64.encodeToString(encrypted, Base64.NO_WRAP)).commit()
    }
    suspend fun bytes(path: String, body: ByteArray? = null, method: String? = null, content: String = "application/json"): ByteArray {
        val base = base(); val auth = token(); val csrfValue = csrf
        return withContext(Dispatchers.IO) {
            val connection = URL(base + path).openConnection() as HttpURLConnection
            try {
                connection.requestMethod = method ?: if (body == null) "GET" else "POST"
                connection.connectTimeout = 15000; connection.readTimeout = 100000
                connection.instanceFollowRedirects = false
                connection.setRequestProperty("Origin", base)
                if (auth.isNotBlank()) connection.setRequestProperty("Authorization", "Bearer $auth")
                if (csrfValue.isNotBlank()) connection.setRequestProperty("X-CSRF-Token", csrfValue)
                if (body != null) { connection.doOutput = true; connection.setRequestProperty("Content-Type", content); connection.outputStream.use { it.write(body) } }
                val success = connection.responseCode in 200..299
                val data = (if (success) connection.inputStream else connection.errorStream)?.use { it.readBytes() } ?: byteArrayOf()
                if (!success) throw IllegalStateException(try { JSONObject(String(data)).optString("error", "Request failed") } catch (_: Exception) { "Creator service unavailable" })
                data
            } finally { connection.disconnect() }
        }
    }
    suspend fun api(path: String, body: JSONObject? = null, method: String? = null): JSONObject = JSONObject(String(bytes(path, body?.toString()?.toByteArray(), method), Charsets.UTF_8))
    suspend fun run(block: suspend () -> Unit) {
        if (busy) return; busy = true; error = null
        try { block() } catch (e: Exception) { error = e.message ?: "Request failed" } finally { busy = false }
    }
    suspend fun refresh() {
        flushLogout()
        if (linkedOrigin != base()) { workspace = null; current = null; rows = emptyList(); selected = emptySet(); quote = null; character = ""; messages = emptyList(); refs = emptyList(); dirty = false; csrf = ""; linkedOrigin = base() }
        val boot = api("/api/bootstrap"); csrf = boot.optString("csrf").takeUnless { it == "null" } ?: ""
        capabilities = boot.optJSONObject("capabilities") ?: JSONObject()
        val user = boot.optJSONObject("user")
        signedIn = user != null
        needsConsent = signedIn && user?.optBoolean("consented") != true && user?.optInt("consented") != 1
        if (!signedIn) { workspace = null; current = null; rows = emptyList(); selected = emptySet(); quote = null; character = ""; messages = emptyList(); refs = emptyList(); dirty = false; return }
        if (needsConsent) { workspace = null; return }
        val next = api("/api/workspace"); workspace = next
        if (!dirty) next.getJSONArray("packs").objects().find { it.getString("id") == current?.optString("id") }?.let { current = it; rows = it.getJSONArray("items").objects() }
        prefs.edit().putString("origin", base()).apply()
    }
    suspend fun acceptTerms() {
        api("/api/account/consent", JSONObject().put("adult", true).put("terms", true)); refresh()
    }
    suspend fun startLogin(): String {
        refresh()
        val verifier = newStudioID() + newStudioID()
        val challenge = Base64.encodeToString(MessageDigest.getInstance("SHA-256").digest(verifier.toByteArray()), Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING)
        val result = api("/api/native/link", JSONObject().put("challenge", challenge).put("app_return", true))
        link = result.getString("id") to verifier
        saveSecret("pending:", JSONObject().put("id",link!!.first).put("verifier",verifier).put("expires",System.currentTimeMillis()+600000).toString())
        return result.getString("url")
    }
    fun cancelLogin() { link = null; saveSecret("pending:", "") }
    suspend fun finishLogin(uri: Uri) {
        if(link == null) readSecret("pending:").takeIf{it.isNotEmpty()}?.let { saved ->
            val value=JSONObject(saved)
            if(value.getLong("expires")>System.currentTimeMillis()) link=value.getString("id") to value.getString("verifier")
        }
        val pair = link ?: error("Sign-in expired. Please try again.")
        require(uri.scheme=="art.lazying.westicker" && uri.host=="auth" && uri.path=="/complete" && uri.getQueryParameter("link")==pair.first) { "This sign-in does not match your device." }
        val result = api("/api/native/link/${pair.first}/exchange", JSONObject().put("verifier", pair.second))
        require(result.has("token")) { "Sign-in has not been approved. Please try again." }
        saveToken(result.getString("token")); cancelLogin(); refresh()
    }
    suspend fun signOut() {
        saveSecret("logout:", JSONObject().put("token",token()).put("csrf",csrf).toString()); saveToken(""); cancelLogin()
        signedIn = false; csrf = ""; workspace = null; current = null; rows = emptyList(); selected = emptySet(); quote = null; character = ""; messages = emptyList(); refs = emptyList(); dirty = false; link = null
        flushLogout()
    }
    private suspend fun flushLogout() {
        val pending=readSecret("logout:"); if(pending.isBlank()) return
        val origin=base();val value=JSONObject(pending)
        val done=withContext(Dispatchers.IO) {
            try { val c=URL(origin+"/api/auth/logout").openConnection() as HttpURLConnection
                try { c.requestMethod="POST"; c.connectTimeout=8000;c.readTimeout=8000;c.instanceFollowRedirects=false
                    c.setRequestProperty("Origin",origin);c.setRequestProperty("Authorization","Bearer ${value.getString("token")}");c.setRequestProperty("X-CSRF-Token",value.getString("csrf"))
                    c.responseCode in 200..299 || c.responseCode==401
                } finally { c.disconnect() }
            } catch(_:Exception) { false }
        }
        if(done) saveSecret("logout:", "")
    }
    suspend fun open(pack: JSONObject) {
        current = pack; rows = pack.getJSONArray("items").objects(); selected = rows.take(1).map { it.getString("id") }.toSet(); dirty = false; creating = false; quote = null
        messages = api("/api/packs/${pack.getString("id")}/conversation").getJSONArray("messages").objects()
    }
    fun edit(index: Int, field: String, value: Any) {
        rows = rows.mapIndexed { i, row -> if (i == index) JSONObject(row.toString()).put(field, value).apply { if (field != "approved") put("approved", false) } else row }; dirty = true; quote = null
    }
    suspend fun save(proposal: JSONArray? = null, revision: Int? = null) {
        val pack = current ?: return
        api("/api/packs/${pack.getString("id")}", JSONObject().put("items", proposal ?: JSONArray(rows)).put("revision", revision ?: pack.getInt("revision")), "PATCH")
        dirty = false; quote = null; refresh()
    }
    suspend fun chat(text: String) {
        if(current==null){
            val id=api("/api/packs",JSONObject().put("title",text.take(60)).put("language","en").put("theme","daily")).getString("id")
            refresh();open(workspace!!.getJSONArray("packs").objects().first{it.getString("id")==id})
        }
        val id = current!!.getString("id")
        val attempt=UUID.randomUUID().toString();messages=messages+JSONObject().put("id",attempt).put("text",text).put("state","working")
        sending=true
        try { api("/api/packs/$id/chat", JSONObject().put("text", text).put("attempt", attempt)) }
        finally { sending=false; messages = api("/api/packs/$id/conversation").getJSONArray("messages").objects() }
    }
    suspend fun getQuote(kind: String) { quote = api("/api/packs/${current!!.getString("id")}/quote", JSONObject().put("kind", kind).put("items", JSONArray(selected.sorted()))) }
    suspend fun generate() {
        val q = quote ?: return; val id = current!!.getString("id")
        val key = "attempt:${base()}:$id:${q.getString("kind")}:${q.getInt("revision")}:${q.getJSONArray("items")}"
        val attempt = prefs.getString(key, null) ?: UUID.randomUUID().toString().also { prefs.edit().putString(key, it).commit() }
        api("/api/packs/$id/generate", JSONObject().put("kind", q.getString("kind")).put("items", q.getJSONArray("items")).put("revision", q.getInt("revision")).put("attempt", attempt).put("consent", true))
        quote = null; refresh()
    }
    suspend fun upload(uri: Uri) {
        require(refs.size < 5)
        val data = withContext(Dispatchers.IO) {
            val input = context.contentResolver.openInputStream(uri)!!.use { stream ->
                val out = ByteArrayOutputStream(); val buffer = ByteArray(8192)
                while (true) { val n = stream.read(buffer); if (n < 0) break; require(out.size() + n <= 20_000_000) { "Choose a photo below 20 MB." }; out.write(buffer, 0, n) }; out.toByteArray()
            }
            val bitmap = if (Build.VERSION.SDK_INT >= 28) ImageDecoder.decodeBitmap(ImageDecoder.createSource(ByteBuffer.wrap(input))) { decoder, info, _ ->
                val scale = minOf(1f, 1600f / maxOf(info.size.width, info.size.height)); decoder.setTargetSize((info.size.width * scale).toInt(), (info.size.height * scale).toInt()); decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            } else {
                val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                BitmapFactory.decodeByteArray(input, 0, input.size, options)
                require(options.outWidth > 0 && options.outHeight > 0)
                options.inJustDecodeBounds = false; options.inSampleSize = maxOf(1, maxOf(options.outWidth, options.outHeight) / 1600)
                BitmapFactory.decodeByteArray(input, 0, input.size, options) ?: error("Invalid image")
            }
            ByteArrayOutputStream().use { out -> bitmap.compress(Bitmap.CompressFormat.PNG, 100, out); bitmap.recycle(); out.toByteArray() }
        }
        val boundary = UUID.randomUUID().toString()
        val body = ByteArrayOutputStream().apply {
            write("--$boundary\r\nContent-Disposition: form-data; name=\"rights\"\r\n\r\nyes\r\n--$boundary\r\nContent-Disposition: form-data; name=\"file\"; filename=\"reference.png\"\r\nContent-Type: image/png\r\n\r\n".toByteArray()); write(data); write("\r\n--$boundary--\r\n".toByteArray())
        }.toByteArray()
        val result = JSONObject(String(bytes("/api/assets", body, content = "multipart/form-data; boundary=$boundary")))
        refs = refs + result.getString("id")
    }
    suspend fun create(name: String, title: String, language: String) {
        if (character.isBlank()) character = api("/api/characters", JSONObject().put("name", name).put("style", "figurine").put("refs", JSONArray(refs))).getString("id")
        api("/api/characters/$character/lock", JSONObject().put("approved", true))
        if(current!=null && current!!.isNull("character_id")){
            api("/api/packs/${current!!.getString("id")}/character",JSONObject().put("character",character).put("revision",current!!.getInt("revision")))
            creating=false;refresh();return
        }
        val id = api("/api/packs", JSONObject().put("character", character).put("title", title).put("language", language).put("theme", "daily")).getString("id")
        refresh(); open(workspace!!.getJSONArray("packs").objects().first { it.getString("id") == id })
    }
    suspend fun export() {
        val data = bytes("/api/packs/${current!!.getString("id")}/export")
        val folder = File(context.cacheDir, "stickers").apply { mkdirs() }
        val output = File(folder, "WeSticker-${UUID.randomUUID()}.zip"); withContext(Dispatchers.IO) { output.writeBytes(data) }
        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", output)
        context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply { type = "application/zip"; putExtra(Intent.EXTRA_STREAM, uri); addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION) }, "Save or share ZIP"))
    }
    val blocked get() = workspace?.optJSONArray("jobs")?.objects()?.any { it.optString("pack_id") == current?.optString("id") && it.optString("state") in listOf("queued", "running", "uncertain") } ?: false
}

@Composable private fun StudioImage(store: CloudStudioStore, id: String, loader: ImageLoader, size: Int = 84) {
    val context = LocalContext.current
    val model = remember(id, store.signedIn, store.origin) { ImageRequest.Builder(context).data(store.base() + "/api/assets/" + id + "?preview=1").addHeader("Authorization", "Bearer " + store.token()).memoryCachePolicy(coil.request.CachePolicy.DISABLED).diskCachePolicy(coil.request.CachePolicy.DISABLED).build() }
    AsyncImage(model, "Character reference", imageLoader = loader, modifier = Modifier.size(size.dp))
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun CloudStudioScreen(store: CloudStudioStore, local: CreatorStore, loader: ImageLoader, section: Int, onSignIn: () -> Unit, onCreate: () -> Unit) {
    val context = LocalContext.current; val scope = rememberCoroutineScope()
    fun run(block: suspend () -> Unit) { scope.launch { store.run(block) } }
    var text by remember { mutableStateOf("") }; var name by remember { mutableStateOf("My character") }; var title by remember { mutableStateOf("Everyday moments") }
    var language by remember { mutableStateOf("en") }; var rights by remember { mutableStateOf(false) }; var showLocal by remember { mutableStateOf(false) }
    var history by remember { mutableStateOf<List<JSONObject>?>(null) }
    var acceptedTerms by remember { mutableStateOf(false) }
    var serviceSettings by remember { mutableStateOf(false) }
    var pane by remember { mutableStateOf(0) }
    var libraryPane by remember { mutableStateOf(0) }
    val scroll=rememberScrollState()
    LaunchedEffect(store.messages.size, store.sending, store.guestMessages.size, store.guestSending) { if(pane==0 || store.usesGuestChat) scroll.animateScrollTo(scroll.maxValue) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri -> if (uri != null) run { store.upload(uri) } }
    LaunchedEffect(Unit) { if (store.origin.isNotBlank()) store.run { store.refresh() }; while (true) { delay(4000); if (!store.busy && store.workspace?.optJSONArray("jobs")?.objects()?.any { it.optString("state") in listOf("queued", "running") } == true) store.run { store.refresh() } } }
    if (showLocal) { CreatorScreen(local, loader) { showLocal = false }; return }
    Scaffold(topBar = { TopAppBar(title = { Text(if(section==2) "Library" else "Create") }, actions = {
        if(section==2) IconButton(enabled=!store.busy,onClick={run{store.refresh()}}){Icon(Icons.Outlined.Refresh,"Refresh library")}
        else IconButton(enabled=store.usesGuestChat||!store.busy&&!store.dirty,onClick={
            if(store.usesGuestChat) store.clearGuestChat()
            else {store.current=null;store.messages=emptyList();store.rows=emptyList();store.creating=false;pane=0}
        }){Icon(Icons.Outlined.Edit,"New chat")}
        IconButton(onClick={serviceSettings=true}){Icon(Icons.Outlined.Settings,"Service settings")}
    }) }, bottomBar={
        if(section==1&&(store.usesGuestChat||!store.creating&&pane==0)) Surface {
            Row(Modifier.fillMaxWidth().imePadding().padding(12.dp),verticalAlignment=Alignment.Bottom,horizontalArrangement=Arrangement.spacedBy(8.dp)) {
                IconButton(enabled=store.usesGuestChat||!store.busy,onClick={if(store.usesGuestChat) showLocal=true else store.creating=true}){
                    Icon(Icons.Outlined.AddPhotoAlternate,if(store.usesGuestChat) "Open saved local photo draft" else "Character references")
                }
                OutlinedTextField(if(store.usesGuestChat) store.guestDraft else text,{
                    if(store.usesGuestChat) store.guestDraft=it.take(GuestChatHistory.MESSAGE_LIMIT) else text=it.take(2000)
                },placeholder={Text("Message Aya…")},modifier=Modifier.weight(1f),minLines=1,maxLines=5)
                IconButton(enabled=if(store.usesGuestChat) store.guestDraft.isNotBlank()&&!store.guestSending else text.isNotBlank()&&!store.busy&&!store.dirty&&!store.blocked,onClick={
                    if(store.usesGuestChat) store.sendGuestChat(scope) else {val input=text;text="";run{store.chat(input)}}
                }){Icon(Icons.Outlined.Send,"Send message")}
            }
        }
    }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).verticalScroll(scroll).padding(16.dp),verticalArrangement=Arrangement.spacedBy(14.dp)) {
            if(section==2) {
                TabRow(selectedTabIndex=libraryPane) {
                    listOf("Creations","Characters").forEachIndexed { index,label ->
                        Tab(selected=libraryPane==index,onClick={libraryPane=index},text={Text(label)})
                    }
                }
                if(libraryPane==0) { TextButton(onClick={showLocal=true}){Text("Open saved local photo draft")}; HorizontalDivider() }
            }
            if(!(section==1&&store.usesGuestChat)) {
                store.error?.let { Text(it, color=MaterialTheme.colorScheme.error) }
                if(store.busy) LinearProgressIndicator(Modifier.fillMaxWidth())
            }
            if(section==1&&store.usesGuestChat) {
                if(store.guestMessages.isEmpty()) {
                    AsyncImage("file:///android_asset/app-icon.png","Aya and Lala",imageLoader=loader,modifier=Modifier.size(80.dp))
                    Text("What shall we make?",style=MaterialTheme.typography.headlineSmall)
                }
                store.guestMessages.forEach { message ->
                    Text(message.text,fontWeight=FontWeight.Bold,modifier=Modifier.align(Alignment.End))
                    if(message.reply!=null) Text(message.reply)
                    else if(message.failure!=null) {
                        Text(message.failure,style=MaterialTheme.typography.bodySmall,color=MaterialTheme.colorScheme.onSurfaceVariant)
                        TextButton(enabled=!store.guestSending,onClick={store.guestDraft=message.text}){Icon(Icons.Outlined.Edit,null);Text("Edit message")}
                    } else Text("Aya is thinking…",style=MaterialTheme.typography.bodySmall)
                }
                store.guestError?.let { Text(it,color=MaterialTheme.colorScheme.error) }
            } else if(!store.signedIn){
                Text(if(libraryPane==0) "Cloud creations" else "Cloud characters",style=MaterialTheme.typography.titleMedium)
                TextButton(enabled=!store.busy,onClick=onSignIn){Icon(Icons.Outlined.AccountCircle,null);Spacer(Modifier.width(8.dp));Text("Sign in to cloud library")}
            } else if(store.needsConsent) {
                Text("Before your first creation",style=MaterialTheme.typography.titleLarge)
                TextButton(onClick={context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(store.base()+"/terms.html")))}){Text("Creator terms")}
                TextButton(onClick={context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(store.base()+"/privacy.html")))}){Text("Privacy policy")}
                Row(verticalAlignment=Alignment.CenterVertically){Checkbox(acceptedTerms,{acceptedTerms=it});Text("I am 18 or older and accept the creator terms",Modifier.weight(1f))}
                Button(enabled=acceptedTerms&&!store.busy,onClick={run{store.acceptTerms()}}){Text("Continue")}
            } else store.workspace?.let { w ->
                val policy=w.getJSONObject("limits");val packs=w.getJSONArray("packs").objects();val chars=w.getJSONArray("characters").objects()
                when {
                    section==2&&libraryPane==0 -> { packs.forEach{p->
                        TextButton(onClick={run{store.open(p);onCreate()}}){Text(p.getString("title"))}
                        Row { p.getJSONArray("items").objects().filter{!it.isNull("asset")}.take(4).forEach{StudioImage(store,it.getString("asset"),loader,60)} };HorizontalDivider()
                    }; if(packs.isEmpty()) Text("No cloud creations yet",color=MaterialTheme.colorScheme.onSurfaceVariant) }
                    section==2 -> { if(chars.isEmpty()) Text("No cloud characters yet",color=MaterialTheme.colorScheme.onSurfaceVariant)
                    chars.forEach{c->
                        Text(c.getString("name"),fontWeight=FontWeight.Bold)
                        Row{val refs=c.getJSONArray("refs");for(i in 0 until minOf(refs.length(),4))StudioImage(store,refs.getString(i),loader,65)}
                        TextButton(onClick={store.character=c.getString("id");store.creating=true;onCreate()}){Text("Create with ${c.getString("name")}")};HorizontalDivider()
                    } }
                    store.creating -> {
                        TextButton(onClick={store.creating=false}){Text("Back to chat")}
                        Text("Who are we creating?",style=MaterialTheme.typography.titleLarge)
                        TextButton(onClick={store.character=""}){Text("New character")}
                        chars.forEach{c->FilterChip(store.character==c.getString("id"),{store.character=c.getString("id")},label={Text(c.getString("name"))})}
                        if(store.character.isBlank()){
                            OutlinedTextField(name,{name=it.take(60)},label={Text("Character name")},modifier=Modifier.fillMaxWidth())
                            Row(verticalAlignment=Alignment.CenterVertically){Checkbox(rights,{rights=it});Text("I have permission to use these references",Modifier.weight(1f))}
                            Button(enabled=rights&&!store.busy&&store.refs.size<5,onClick={picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))}){Icon(Icons.Outlined.AddPhotoAlternate,null);Text("Upload reference (${store.refs.size}/5)")}
                            store.refs.forEach{id->Row(verticalAlignment=Alignment.CenterVertically){StudioImage(store,id,loader);IconButton(onClick={store.refs=store.refs.filter{it!=id}}){Icon(Icons.Outlined.Close,"Remove reference")}}}
                        }
                        OutlinedTextField(title,{title=it.take(60)},label={Text("Collection name")},modifier=Modifier.fillMaxWidth())
                        Row(horizontalArrangement=Arrangement.spacedBy(6.dp)){listOf("en" to "English","zh" to "中文","ja" to "日本語").forEach{(id,label)->FilterChip(language==id,{language=id},label={Text(label)})}}
                        Button(enabled=!store.busy&&(store.character.isNotBlank()||rights&&store.refs.isNotEmpty()),onClick={run{store.create(name,title,language)}}){Text("Approve references & start")}
                    }
                    store.current==null -> {
                        AsyncImage("file:///android_asset/app-icon.png","Aya and Lala",imageLoader=loader,modifier=Modifier.size(80.dp))
                        Text("What shall we make?",style=MaterialTheme.typography.headlineSmall)
                    }
                    else -> {
                        val p=store.current!!;Text(p.getString("title"),style=MaterialTheme.typography.titleLarge)
                        TabRow(selectedTabIndex=pane){listOf("Chat","Sticker plan").forEachIndexed{i,label->Tab(selected=pane==i,onClick={pane=i},text={Text(label)})}}
                        if(pane==0){
                        store.messages.forEach{m->
                            Text(m.getString("text"),fontWeight=FontWeight.Bold)
                            m.optJSONObject("result")?.let{result->Text(result.getString("reply"));result.optJSONArray("items")?.let{proposed->
                                proposed.objects().forEach{row->Text(row.getString("label"),fontWeight=FontWeight.Medium);Text(row.optString("action"),style=MaterialTheme.typography.bodySmall);HorizontalDivider()}
                                TextButton(enabled=!store.busy&&!store.dirty&&!store.blocked&&result.optInt("revision",-1)==p.getInt("revision"),onClick={run{store.save(proposed,result.getInt("revision"))}}){Text("Apply table")}
                            }}
                            if(m.optString("state")=="working")Text("Aya is thinking…",style=MaterialTheme.typography.bodySmall)
                            if(m.optString("state")=="failed")Text("Reply interrupted. Your draft is saved.",style=MaterialTheme.typography.bodySmall)
                        }
                        }else{
                        if(p.isNull("character_id")) Button(onClick={store.creating=true}){Text("Choose character references")}
                        HorizontalDivider();Text("Sticker plan",style=MaterialTheme.typography.titleMedium)
                        store.rows.forEachIndexed{i,row->val id=row.getString("id")
                            Row(verticalAlignment=Alignment.Top){Checkbox(store.selected.contains(id),{checked->store.selected=if(checked)store.selected+id else store.selected-id;store.quote=null})
                                Column(Modifier.weight(1f),verticalArrangement=Arrangement.spacedBy(6.dp)){
                                    OutlinedTextField(row.getString("label"),{store.edit(i,"label",it.take(32))},label={Text("Caption ${i+1}")},enabled=!store.busy&&!store.blocked,modifier=Modifier.fillMaxWidth())
                                    OutlinedTextField(row.optString("action",""),{store.edit(i,"action",it.take(500))},label={Text("Action ${i+1}")},enabled=!store.busy&&!store.blocked,modifier=Modifier.fillMaxWidth(),minLines=2)
                                    if(!row.isNull("asset")){StudioImage(store,row.getString("asset"),loader,120);Row(verticalAlignment=Alignment.CenterVertically){Checkbox(row.optBoolean("approved"),{store.edit(i,"approved",it)},enabled=!store.busy&&!store.blocked);Text("Approve reference")}}
                                }
                                IconButton(enabled=store.rows.size>1&&!store.blocked&&!store.busy,onClick={store.rows=store.rows.filter{it.getString("id")!=id};store.selected=store.selected-id;store.dirty=true}){Icon(Icons.Outlined.DeleteOutline,"Remove sticker")}
                            };HorizontalDivider()
                        }
                        Row {TextButton(enabled=!store.busy&&!store.blocked&&store.rows.size<policy.getInt("pack_size"),onClick={store.rows=store.rows+JSONObject().put("id",newStudioID()).put("label","Hello").put("action","").put("asset",JSONObject.NULL).put("approved",false);store.dirty=true}){Text("Add word")}
                            Button(enabled=store.dirty&&!store.busy&&!store.blocked,onClick={run{store.save()}}){Text("Save table")}}
                        w.getJSONArray("jobs").objects().filter{it.getString("pack_id")==p.getString("id")}.take(3).forEach{job->Text("${job.getString("kind")} · ${job.getString("state")}");LinearProgressIndicator(progress={job.getInt("progress")/100f},modifier=Modifier.fillMaxWidth());if(!job.isNull("error"))Text(job.getString("error"),color=MaterialTheme.colorScheme.error)}
                        listOf("photo" to "Use uploaded photo","ai" to "Generate references","animate" to "Animate approved").forEach{(kind,label)->
                            val available = kind=="photo" || store.capabilities.optBoolean(if(kind=="ai") "ai_images" else "animation")
                            OutlinedButton(enabled=available&&!store.busy&&!store.dirty&&!store.blocked&&store.selected.isNotEmpty(),onClick={run{store.getQuote(kind)}}){Text(label)}
                        }
                        if(!store.capabilities.optBoolean("ai_images")) Text("AI image generation is unavailable on this service. Photo creations and saved drafts remain available.",style=MaterialTheme.typography.bodySmall)
                        store.quote?.let{q->Text("${q.getJSONArray("items").length()} sticker(s) · ${q.getInt("credits")} credits",fontWeight=FontWeight.Bold);if(!q.isNull("reason"))Text(q.getString("reason"));Button(enabled=q.getBoolean("can_generate")&&!store.busy,onClick={run{store.generate()}}){Text("Confirm generation")};TextButton(onClick={store.quote=null}){Text("Cancel")}}
                        Button(enabled=!store.busy&&!store.dirty&&store.rows.all{it.optBoolean("approved")},onClick={run{store.export()}}){Text("Export reviewed ZIP")}
                        TextButton(onClick={run{history=store.api("/api/packs/${p.getString("id")}/versions").getJSONArray("versions").objects().flatMap{it.getJSONArray("items").objects()}}}){Text("Version history")}
                        }
                    }
                }
            }
        }
    }
    if(serviceSettings) AlertDialog(onDismissRequest={serviceSettings=false},title={Text("Service settings")},text={
        Column(verticalArrangement=Arrangement.spacedBy(12.dp)) {
            OutlinedTextField(store.origin,{store.origin=it},label={Text("HTTPS creator service")},modifier=Modifier.fillMaxWidth())
            runCatching { store.base() }.getOrNull()?.let { base ->
                Row { listOf("Terms" to "/terms.html","Privacy" to "/privacy.html").forEach { (label,path) ->
                    TextButton(onClick={context.startActivity(Intent(Intent.ACTION_VIEW,Uri.parse(base+path)))}){Text(label)}
                } }
            }
        }
    },confirmButton={TextButton(onClick={serviceSettings=false;run{store.refresh()}}){Text("Done")}})
    history?.let{items->AlertDialog(onDismissRequest={history=null},title={Text("Preserved versions")},text={Column(Modifier.verticalScroll(rememberScrollState())){items.forEach{r->if(!r.isNull("asset")){StudioImage(store,r.getString("asset"),loader,140);Text(r.getString("label"))}}}},confirmButton={TextButton(onClick={history=null}){Text("Close")}})}
}
