package art.lazying.westicker

import android.content.Context
import android.content.Intent
import android.graphics.*
import android.net.Uri
import android.os.Build
import android.util.AtomicFile
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.FileProvider
import coil.ImageLoader
import coil.compose.AsyncImage
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.nio.ByteBuffer
import java.util.UUID

data class CreatorDraft(val name: String = "My character", val title: String = "My first pack",
    val language: String = "en", val theme: String = "daily", val labels: List<String> = emptyList(),
    val photo: String? = null, val rights: Boolean = false, val locked: Boolean = false)

class CreatorStore(private val context: Context) {
    private val root = File(context.filesDir, "studio").apply { mkdirs() }
    private val file = AtomicFile(File(root, "draft.json"))
    val plans = JSONObject(context.assets.open("creator-plans.json").bufferedReader().use { it.readText() })
    var draft by mutableStateOf(CreatorDraft())
        private set
    var error by mutableStateOf<String?>(null)
    private var writable = true
    init {
        if (file.baseFile.exists()) try {
            val data = JSONObject(String(file.readFully(), Charsets.UTF_8))
            draft = CreatorDraft(data.getString("name"), data.getString("title"), data.getString("language"),
                data.getString("theme"), data.getJSONArray("labels").let { a -> (0 until a.length()).map { a.getString(it) } },
                data.optString("photo").takeIf { it.matches(Regex("[A-Za-z0-9-]+\\.png")) },
                data.optBoolean("rights"), data.optBoolean("locked"))
        } catch (_: Exception) { writable = false; error = "The saved draft could not be opened. Its files were preserved." }
        if (draft.labels.isEmpty()) draft = draft.copy(labels = captions("daily", "en"))
    }
    fun photoFile() = draft.photo?.let { File(root, it) }
    fun captions(theme: String, language: String): List<String> {
        val a = plans.getJSONObject("themes").getJSONObject(theme).getJSONArray(language)
        return (0 until a.length()).map { a.getString(it) }
    }
    fun match(text: String): String {
        val keys = plans.getJSONObject("keywords")
        return keys.keys().asSequence().sorted().map { key ->
            val words = keys.getJSONArray(key)
            key to (0 until words.length()).count { text.contains(words.getString(it), ignoreCase = true) }
        }.filter { it.second > 0 }.sortedWith(compareByDescending<Pair<String,Int>> { it.second }.thenBy { it.first })
            .firstOrNull()?.first ?: draft.theme
    }
    fun update(value: CreatorDraft) {
        draft = value
        if (!writable) return
        val json = JSONObject().put("name", value.name).put("title", value.title).put("language", value.language)
            .put("theme", value.theme).put("labels", JSONArray(value.labels)).put("photo", value.photo ?: "")
            .put("rights", value.rights).put("locked", value.locked)
        var stream: java.io.FileOutputStream? = null
        try { stream = file.startWrite(); stream.write(json.toString().toByteArray()); file.finishWrite(stream) }
        catch (_: Exception) { file.failWrite(stream); error = "Draft could not be saved. Please try again." }
    }
    suspend fun importPhoto(uri: Uri) {
        val name = withContext(Dispatchers.IO) {
            val bytes = context.contentResolver.openInputStream(uri)!!.use { input ->
                val out = ByteArrayOutputStream(); val block = ByteArray(8192)
                while (true) { val n = input.read(block); if (n < 0) break; require(out.size()+n <= 20_000_000); out.write(block,0,n) }; out.toByteArray()
            }
            val image = if (Build.VERSION.SDK_INT >= 28) ImageDecoder.decodeBitmap(ImageDecoder.createSource(ByteBuffer.wrap(bytes))) { decoder, info, _ ->
                val ratio = minOf(1f, 1200f / maxOf(info.size.width, info.size.height)); decoder.setTargetSize((info.size.width*ratio).toInt(), (info.size.height*ratio).toInt()); decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            } else {
                val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                BitmapFactory.decodeByteArray(bytes,0,bytes.size,options)
                require(options.outWidth > 0 && options.outHeight > 0)
                options.inJustDecodeBounds = false; options.inSampleSize = maxOf(1, maxOf(options.outWidth,options.outHeight)/1200)
                BitmapFactory.decodeByteArray(bytes,0,bytes.size,options) ?: throw IllegalArgumentException("Invalid photo")
            }
            val name = UUID.randomUUID().toString()+".png"
            File(root,name).outputStream().use { require(image.compress(Bitmap.CompressFormat.PNG,100,it)) }
            image.recycle(); name
        }
        update(draft.copy(photo = name, rights = false, locked = false))
    }
    suspend fun export(index: Int) {
        require(draft.rights && draft.locked)
        val snapshot = draft
        val output = withContext(Dispatchers.IO) {
            val source = BitmapFactory.decodeFile(photoFile()!!.path) ?: throw IllegalArgumentException("Invalid photo")
            val result = Bitmap.createBitmap(320,320,Bitmap.Config.ARGB_8888)
            val canvas = Canvas(result); val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
            val ratio = minOf(304f/source.width,280f/source.height)
            val w=source.width*ratio;val h=source.height*ratio
            canvas.drawBitmap(source,null,RectF((320-w)/2,(292-h)/2,(320+w)/2,(292+h)/2),paint)
            paint.typeface=Typeface.create(Typeface.DEFAULT,Typeface.BOLD);paint.textAlign=Paint.Align.CENTER
            val label=snapshot.labels[index]; paint.textSize=25f
            while(paint.measureText(label)>300 && paint.textSize>9)paint.textSize-=1f
            paint.style=Paint.Style.STROKE;paint.strokeWidth=3f;paint.color=Color.BLACK;canvas.drawText(label,160f,307f,paint)
            paint.style=Paint.Style.FILL;paint.color=Color.WHITE;canvas.drawText(label,160f,307f,paint)
            val folder=File(context.cacheDir,"stickers").apply { mkdirs() }
            val target=File(folder,"photo-${UUID.randomUUID()}.png")
            target.outputStream().use { result.compress(Bitmap.CompressFormat.PNG,100,it) }
            source.recycle();result.recycle();target
        }
        val content=FileProvider.getUriForFile(context,"${context.packageName}.fileprovider",output)
        context.startActivity(Intent.createChooser(Intent(Intent.ACTION_SEND).apply { type="image/png";putExtra(Intent.EXTRA_STREAM,content);addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION) },"Save or share photo sticker"))
    }
}

@Composable fun StudioRoot(packs: List<Pack>, loader: ImageLoader, save: suspend(Pack,Sticker,String)->Unit) {
    val context=LocalContext.current
    val store=remember { CreatorStore(context) }
    val cloud=remember { CloudStudioStore(context) }
    val billing=remember { NativeBillingStore(cloud) }
    val scope=rememberCoroutineScope()
    var tab by rememberSaveable { mutableStateOf(0) }
    var authDestination by rememberSaveable { mutableStateOf<Int?>(null) }
    var showLocalDraft by rememberSaveable { mutableStateOf(false) }
    fun navigate(destination: Int) {
        if(destination!=0&&!cloud.signedIn) { authDestination=destination;tab=0 }
        else tab=destination
    }
    val activity=context as? MainActivity
    val signIn: (StudioProvider) -> Unit = { provider -> scope.launch { cloud.run { requireNotNull(activity).beginAuthentication(cloud.startLogin(provider)) } } }
    LaunchedEffect(activity?.authResult, activity?.authCancelled) {
        while(cloud.busy) kotlinx.coroutines.delay(50)
        if(activity?.authResult!=null){
            val uri=activity.authResult!!
            cloud.run{cloud.finishLogin(uri)}
            // Consuming an effect key before the exchange suspends cancels it.
            if(activity.authResult==uri) activity.clearAuthenticationResult()
        }
        else if(activity?.authCancelled==true){activity.clearAuthenticationResult();cloud.cancelLogin();authDestination=null;tab=0}
    }
    LaunchedEffect(cloud.signedIn) {
        if(cloud.signedIn) { authDestination?.let { tab=it;authDestination=null } }
        else if(tab!=0) { authDestination=tab;tab=0 }
    }
    val lifecycleOwner=androidx.lifecycle.compose.LocalLifecycleOwner.current
    DisposableEffect(billing,lifecycleOwner) {
        val observer=androidx.lifecycle.LifecycleEventObserver { _,event ->
            if(event==androidx.lifecycle.Lifecycle.Event.ON_RESUME){billing.attach();billing.restore()}
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer);billing.close() }
    }
    LaunchedEffect(Unit) { cloud.run { cloud.refresh() } }
    val billingSession=cloud.billingSession()
    LaunchedEffect(billingSession?.origin,billingSession?.token) { billing.attach() }
    val labels=listOf("Stickers","Create","Library","Account")
    val icons=listOf(Icons.Outlined.SentimentSatisfiedAlt,Icons.Outlined.Forum,Icons.Outlined.CollectionsBookmark,Icons.Outlined.AccountCircle)
    Scaffold(contentWindowInsets=WindowInsets(0,0,0,0),bottomBar={ NavigationBar {
        labels.forEachIndexed { index,label -> NavigationBarItem(selected=tab==index,onClick={navigate(index)},icon={Icon(icons[index],label)},label={Text(label)}) }
    } }) { padding ->
        Box(Modifier.fillMaxSize().padding(padding)) {
            when(if(cloud.signedIn) tab else 0) {
                0 -> Catalog(packs,loader,save)
                3 -> BillingAccountScreen(cloud,billing)
                else -> CloudStudioScreen(cloud,store,loader,tab,onCreate={navigate(1)})
            }
        }
    }
    if(authDestination!=null) Dialog(
        onDismissRequest={if(!cloud.busy){cloud.cancelLogin();authDestination=null}},
        properties=DialogProperties(usePlatformDefaultWidth=false,dismissOnBackPress=!cloud.busy,dismissOnClickOutside=false)
    ) {
        Surface(Modifier.fillMaxSize()) {
            StudioLoginScreen(cloud,loader,signIn,
                dismiss={cloud.cancelLogin();authDestination=null},
                openLocalDraft=if(authDestination==2) {{authDestination=null;showLocalDraft=true}} else null)
        }
    }
    if(showLocalDraft) Dialog(onDismissRequest={showLocalDraft=false},properties=DialogProperties(usePlatformDefaultWidth=false)) {
        Surface(Modifier.fillMaxSize()) {
            CreatorScreen(store,loader,onClose={showLocalDraft=false},openAgent={showLocalDraft=false;navigate(1)})
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun CreatorScreen(store: CreatorStore, loader: ImageLoader, onClose: (() -> Unit)? = null, openAgent: ()->Unit) {
    val scope=rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    var selected by rememberSaveable { mutableStateOf(0) }
    val picker=rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri ->
        if(uri!=null) { busy=true;scope.launch { try { store.importPhoto(uri) } catch(_:Exception){store.error="Choose a supported photo smaller than 20 MB."}finally{busy=false} } }
    }
    val draft=store.draft
    Scaffold(topBar={CompactStudioTopBar("Create",navigationIcon={
        onClose?.let { close -> IconButton(onClick=close){Icon(Icons.Outlined.Close,"Close local draft")} }
    },actions={IconButton(onClick=openAgent){Icon(Icons.Outlined.Forum,"Ask Agent")}})}){padding->
        Column(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(16.dp),verticalArrangement=Arrangement.spacedBy(14.dp)) {
            Text(if(draft.locked)"Character locked · On this device" else "Private draft · On this device",style=MaterialTheme.typography.labelLarge)
            Row(verticalAlignment=Alignment.CenterVertically,horizontalArrangement=Arrangement.spacedBy(14.dp)) {
                AsyncImage(store.photoFile()?:"file:///android_asset/app-icon.png",null,modifier=Modifier.size(96.dp),imageLoader=loader)
                Column(Modifier.weight(1f)) {
                    OutlinedTextField(draft.name,{store.update(draft.copy(name=it.take(60)))},label={Text("Character name")},singleLine=true)
                    TextButton(enabled=!busy,onClick={picker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))}){Text(if(draft.photo==null)"Choose photo" else "Replace photo")}
                }
            }
            if(busy)LinearProgressIndicator(Modifier.fillMaxWidth())
            Row(verticalAlignment=Alignment.CenterVertically){Checkbox(draft.rights,{store.update(draft.copy(rights=it,locked=if(it)draft.locked else false))});Text("I have permission to use this photo",Modifier.weight(1f))}
            Row(verticalAlignment=Alignment.CenterVertically){Switch(draft.locked,{store.update(draft.copy(locked=it))},enabled=draft.photo!=null&&draft.rights);Text("Keep this character reference",Modifier.padding(start=10.dp).weight(1f))}
            OutlinedTextField(draft.title,{store.update(draft.copy(title=it.take(80)))},Modifier.fillMaxWidth(),label={Text("Pack title")})
            Row(horizontalArrangement=Arrangement.spacedBy(6.dp)){listOf("en" to "English","ja" to "日本語","zh" to "中文").forEach{(id,label)->FilterChip(draft.language==id,{store.update(draft.copy(language=id))},label={Text(label)})}}
            draft.labels.forEachIndexed { index,label ->
                Row(verticalAlignment=Alignment.CenterVertically){RadioButton(selected==index,{selected=index});OutlinedTextField(label,{val updated=draft.labels.toMutableList();updated[index]=it.take(48);store.update(draft.copy(labels=updated))},Modifier.weight(1f),label={Text("Caption ${index+1}")})}
            }
            Box(Modifier.fillMaxWidth().aspectRatio(1f),contentAlignment=Alignment.BottomCenter){
                AsyncImage(store.photoFile(),"Photo sticker preview",modifier=Modifier.fillMaxSize().padding(8.dp),imageLoader=loader)
                Surface(color=MaterialTheme.colorScheme.surface.copy(alpha=.9f)){Text(draft.labels.getOrElse(selected){""},Modifier.padding(10.dp),style=MaterialTheme.typography.titleLarge,fontWeight=FontWeight.Bold)}
            }
            Button(enabled=draft.photo!=null&&draft.rights&&draft.locked&&!busy,onClick={busy=true;scope.launch{try{store.export(selected.coerceAtMost(draft.labels.lastIndex))}catch(_:Exception){store.error="Could not export photo sticker."}finally{busy=false}}}){Icon(Icons.Outlined.Share,null);Text("Export photo sticker",Modifier.padding(start=8.dp))}
            Text("Cloud AI: not connected",style=MaterialTheme.typography.bodySmall)
            store.error?.let{Text(it,color=MaterialTheme.colorScheme.error)}
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable fun AgentScreen(store: CreatorStore,openCreate:()->Unit) {
    var brief by rememberSaveable { mutableStateOf("") }
    var plan by rememberSaveable { mutableStateOf(emptyList<String>()) }
    var matched by rememberSaveable { mutableStateOf("daily") }
    var confirm by remember { mutableStateOf(false) }
    Scaffold(topBar={CompactStudioTopBar("Agent")}){padding->
        Column(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(16.dp),verticalArrangement=Arrangement.spacedBy(16.dp)){
            Text("On-device planner",style=MaterialTheme.typography.labelLarge)
            Text(store.draft.title,style=MaterialTheme.typography.titleLarge)
            OutlinedTextField(brief,{brief=it.take(2000)},Modifier.fillMaxWidth(),label={Text("Pack brief")},minLines=3)
            Row(Modifier.horizontalScroll(rememberScrollState()),horizontalArrangement=Arrangement.spacedBy(4.dp)){listOf("daily" to "Daily","office" to "Work","couple" to "Couple","sports" to "Sports").forEach{(id,label)->FilterChip(store.draft.theme==id,{store.update(store.draft.copy(theme=id))},label={Text(label)})}}
            Button(onClick={matched=store.match(brief);plan=store.captions(matched,store.draft.language)}){Icon(Icons.Outlined.AutoAwesome,null);Text("Prepare captions",Modifier.padding(start=8.dp))}
            if(plan.isNotEmpty()){
                Text("${plan.size} captions · $matched",fontWeight=FontWeight.Bold)
                plan.forEach{Text(it)}
                Button(onClick={confirm=true}){Text("Apply to draft")}
            }
            HorizontalDivider()
            Text("Cloud AI: not connected")
            Text("WeChat upload: not connected")
        }
    }
    if(confirm)AlertDialog(onDismissRequest={confirm=false},title={Text("Replace this draft's captions?")},confirmButton={TextButton(onClick={store.update(store.draft.copy(theme=matched,labels=plan));confirm=false;openCreate()}){Text("Apply captions")}},dismissButton={TextButton(onClick={confirm=false}){Text("Cancel")}})
}
