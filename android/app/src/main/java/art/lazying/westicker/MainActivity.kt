package art.lazying.westicker

import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import coil.ImageLoader
import coil.compose.AsyncImage
import coil.compose.rememberAsyncImagePainter
import coil.decode.GifDecoder
import coil.decode.ImageDecoderDecoder
import coil.request.ImageRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URI

data class Sticker(val id: String, val label: String, val gif: String, val poster: String)
data class Pack(val id: String, val english: String, val name: String, val banner: String,
    val stickers: Map<String, List<Sticker>>)

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val catalog = JSONObject(assets.open("catalog.json").bufferedReader().use { it.readText() }).getJSONArray("packs")
        val packs = (0 until catalog.length()).map { index ->
            val p = catalog.getJSONObject(index)
            val all = p.getJSONObject("stickers")
            Pack(p.getString("id"), p.getString("english"), p.getString("name"), p.getString("banner"),
                listOf("en", "zh", "ja").associateWith { language ->
                    val a = all.getJSONArray(language)
                    (0 until a.length()).map { i -> a.getJSONObject(i).let {
                        Sticker(it.getString("id"), it.getString("label"), it.getString("gif"), it.getString("poster"))
                    } }
                }
            )
        }
        val loader = ImageLoader.Builder(this).components {
            if (Build.VERSION.SDK_INT >= 28) add(ImageDecoderDecoder.Factory()) else add(GifDecoder.Factory())
        }.build()
        setContent {
            MaterialTheme(colorScheme = lightColorScheme(primary = Color(0xFFCB315E),
                primaryContainer = Color(0xFFFFE4ED), onPrimaryContainer = Color(0xFF762340),
                secondary = Color(0xFF007F79), surface = Color.White,
                background = Color(0xFFFAFAFC))) {
                Catalog(packs, loader, ::shareSticker)
            }
        }
    }

    private suspend fun shareSticker(pack: Pack, sticker: Sticker, language: String) {
        val file = withContext(Dispatchers.IO) {
            val uri = URI(sticker.gif)
            require(uri.scheme == "https" && uri.host == "aya.lazying.art" && uri.port == -1 &&
                uri.userInfo == null && uri.path.startsWith("/media/") && uri.path.endsWith(".gif"))
            val connection = uri.toURL().openConnection() as HttpURLConnection
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 15000
            connection.readTimeout = 30000
            val bytes = try {
                require(connection.responseCode == 200)
                connection.inputStream.use { input ->
                    val output = ByteArrayOutputStream()
                    val buffer = ByteArray(8192)
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        require(output.size() + read <= 3_000_000)
                        output.write(buffer, 0, read)
                    }
                    output.toByteArray()
                }
            } finally { connection.disconnect() }
            require(bytes.size > 6 && String(bytes.copyOfRange(0, 6)) in listOf("GIF87a", "GIF89a"))
            val folder = File(cacheDir, "stickers").apply { mkdirs() }
            val filename = "${pack.id}-$language-${sticker.id}.gif"
            require(filename.matches(Regex("[A-Za-z0-9_-]+\\.gif")))
            File(folder, filename).apply { writeBytes(bytes) }
        }
        val content = FileProvider.getUriForFile(this, "$packageName.fileprovider", file)
        val intent = Intent(Intent.ACTION_SEND).apply {
            type = "image/gif"
            putExtra(Intent.EXTRA_STREAM, content)
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
        }
        startActivity(Intent.createChooser(intent, "Save or share sticker"))
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun Catalog(packs: List<Pack>, loader: ImageLoader,
    save: suspend (Pack, Sticker, String) -> Unit) {
    val context = LocalContext.current
    val preferences = remember { context.getSharedPreferences("catalog", 0) }
    var language by remember { mutableStateOf(preferences.getString("language", "en") ?: "en") }
    var favorites by remember { mutableStateOf(preferences.getStringSet("favorites", emptySet())!!.toSet()) }
    var onlySaved by remember { mutableStateOf(false) }
    var query by remember { mutableStateOf("") }
    var selected by remember { mutableStateOf(packs.first().id) }
    var playing by remember { mutableStateOf(true) }
    var preview by remember { mutableStateOf<Pair<Pack, Sticker>?>(null) }
    var info by remember { mutableStateOf(false) }
    var saving by remember { mutableStateOf(false) }
    val snack = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val filtered = packs.filter { (!onlySaved || it.id in favorites) &&
        (it.english + it.name).contains(query, ignoreCase = true) }
    val active = filtered.find { it.id == selected } ?: filtered.firstOrNull()
    fun download(pack: Pack, sticker: Sticker) {
        if (saving) return
        saving = true
        scope.launch {
            try { save(pack, sticker, language) }
            catch (_: Exception) { snack.showSnackbar("Couldn't save this GIF. Check your connection and try again.") }
            finally { saving = false }
        }
    }
    Scaffold(topBar = {
        TopAppBar(title = { Text("WeSticker", fontWeight = FontWeight.Bold) }, actions = {
            IconButton(onClick = { onlySaved = !onlySaved }) {
                Icon(if (onlySaved) Icons.Outlined.Favorite else Icons.Outlined.FavoriteBorder, "Saved collections")
            }
            IconButton(onClick = { info = true }) { Icon(Icons.Outlined.Info, "About this beta") }
        })
    }, snackbarHost = { SnackbarHost(snack) }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp)) {
            Text("Sticker collections", style = MaterialTheme.typography.headlineSmall)
            OutlinedTextField(query, { query = it }, Modifier.fillMaxWidth().padding(vertical = 10.dp),
                singleLine = true, label = { Text("Search collections") },
                leadingIcon = { Icon(Icons.Outlined.Search, null) })
            BoxWithConstraints(Modifier.weight(1f)) {
                val wide = maxWidth >= 700.dp
                @Composable fun packItem(pack: Pack, modifier: Modifier) {
                    Surface(onClick = { selected = pack.id }, modifier = modifier, shape = RoundedCornerShape(8.dp),
                        color = if (active?.id == pack.id) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surface) {
                        Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
                            AsyncImage("file:///android_asset" + pack.stickers[language]!!.first().poster,
                                null, modifier = Modifier.size(44.dp), imageLoader = loader)
                            Text(pack.english, Modifier.padding(start = 8.dp).weight(1f), maxLines = 2,
                                style = MaterialTheme.typography.labelLarge)
                        }
                    }
                }
                @Composable fun content(modifier: Modifier) {
                    Column(modifier) {
                        if (active == null) {
                            Text("No collections found", Modifier.padding(20.dp))
                        } else {
                            Row(Modifier.padding(vertical = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Text(active.english, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                    Text("${active.stickers[language]!!.size} GIFs", style = MaterialTheme.typography.bodySmall)
                                }
                                IconButton(onClick = {
                                    favorites = if (active.id in favorites) favorites - active.id else favorites + active.id
                                    preferences.edit().putStringSet("favorites", favorites).apply()
                                }) { Icon(if (active.id in favorites) Icons.Outlined.Favorite else Icons.Outlined.FavoriteBorder, "Save collection") }
                            }
                            Row(horizontalArrangement = Arrangement.spacedBy(6.dp), verticalAlignment = Alignment.CenterVertically) {
                                listOf("en" to "English", "ja" to "日本語", "zh" to "中文").forEach { (id, label) ->
                                    FilterChip(language == id, {
                                        language = id; preferences.edit().putString("language", id).apply()
                                    }, label = { Text(label) })
                                }
                                Spacer(Modifier.weight(1f))
                                IconButton(onClick = { playing = !playing }) {
                                    Icon(if (playing) Icons.Outlined.Pause else Icons.Outlined.PlayArrow,
                                        if (playing) "Pause animations" else "Play animations")
                                }
                            }
                            LazyVerticalGrid(columns = GridCells.Adaptive(110.dp),
                                horizontalArrangement = Arrangement.spacedBy(8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                items(active.stickers[language]!!, key = { active.id + language + it.id }) { sticker ->
                                    Surface(shape = RoundedCornerShape(8.dp), color = MaterialTheme.colorScheme.surface) {
                                        Column {
                                            val poster = rememberAsyncImagePainter("file:///android_asset" + sticker.poster, imageLoader = loader)
                                            AsyncImage(ImageRequest.Builder(context).data(if (playing) sticker.gif else
                                                "file:///android_asset" + sticker.poster).build(), sticker.label,
                                                placeholder = poster, error = poster,
                                                modifier = Modifier.fillMaxWidth().aspectRatio(1f)
                                                    .semantics { contentDescription = "Preview " + sticker.label }
                                                    .clickable { preview = active to sticker }, imageLoader = loader)
                                            Row(Modifier.padding(start = 8.dp), verticalAlignment = Alignment.CenterVertically) {
                                                Text(sticker.label, Modifier.weight(1f), maxLines = 2,
                                                    style = MaterialTheme.typography.labelMedium)
                                                IconButton(enabled = !saving, onClick = { download(active, sticker) }) {
                                                    Icon(Icons.Outlined.FileDownload, "Save GIF " + sticker.label, Modifier.size(18.dp))
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                if (wide) Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                    LazyColumn(Modifier.width(210.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        items(filtered) { pack -> packItem(pack, Modifier.fillMaxWidth()) }
                    }
                    content(Modifier.weight(1f))
                } else Column {
                    LazyRow(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        items(filtered) { pack -> packItem(pack, Modifier.width(185.dp)) }
                    }
                    content(Modifier.weight(1f))
                }
            }
        }
    }
    preview?.let { (pack, sticker) ->
        AlertDialog(onDismissRequest = { preview = null }, title = { Text(sticker.label) },
            text = {
                val poster = rememberAsyncImagePainter("file:///android_asset" + sticker.poster, imageLoader = loader)
                AsyncImage(if (playing) sticker.gif else "file:///android_asset" + sticker.poster,
                    sticker.label, modifier = Modifier.fillMaxWidth().aspectRatio(1f), imageLoader = loader,
                    placeholder = poster, error = poster)
            },
            confirmButton = { TextButton(enabled = !saving, onClick = { download(pack, sticker) }) { Text("Save GIF") } },
            dismissButton = { TextButton(onClick = { preview = null }) { Text("Close") } })
    }
    if (info) AlertDialog(onDismissRequest = { info = false }, title = { Text("WeSticker · Catalog beta") },
        text = { Text("Aya, Lala, Sasa and Zhuangzi the robot.\n\nFavourites stay on this device. GIF downloads connect to aya.lazying.art. No account, analytics or payment is required.\n\nAI creation, login and subscriptions are not part of this test build.") },
        confirmButton = { TextButton(onClick = { info = false }) { Text("Done") } })
}
