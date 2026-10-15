package art.lazying.westicker

import java.io.File
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URI
import org.json.JSONObject

object PublicCatalogStore {
    fun parse(raw: String, remote: Boolean = false): List<Pack> {
        val catalog = JSONObject(raw).getJSONArray("packs")
        require(catalog.length() in 1..200)
        val packs = (0 until catalog.length()).map { index ->
            val p = catalog.getJSONObject(index)
            val all = p.getJSONObject("stickers")
            Pack(p.getString("id"), p.getString("english"), p.getString("name"), p.getString("banner"),
                listOf("en", "zh", "ja").associateWith { language ->
                    val rows = all.getJSONArray(language)
                    require(rows.length() in 1..64)
                    (0 until rows.length()).map { i -> rows.getJSONObject(i).let {
                        Sticker(it.getString("id"), it.getString("label"), it.getString("gif"), it.getString("poster"))
                    } }.also { require(it.map { s -> s.id }.distinct().size == it.size) }
                })
        }
        require(packs.map { it.id }.distinct().size == packs.size)
        if (remote) packs.forEach { pack ->
            (listOf(pack.banner) + pack.stickers.values.flatten().flatMap { listOf(it.gif, it.poster) }).forEach {
                val uri = URI(it)
                require(uri.scheme == "https" && uri.host == "aya.lazying.art" && uri.port == -1 &&
                    uri.userInfo == null && uri.query == null && uri.fragment == null &&
                    uri.path.startsWith("/media/") && !it.contains(".."))
            }
        }
        return packs
    }

    fun load(cache: File): List<Pack>? {
        val saved = runCatching { parse(cache.readText(), true) }.getOrNull()
        if (saved != null && System.currentTimeMillis() - cache.lastModified() < 300_000) return saved
        return runCatching {
            val connection = URI("https://westicker.lazying.art/api/catalog").toURL().openConnection() as HttpURLConnection
            connection.instanceFollowRedirects = false
            connection.connectTimeout = 8000
            connection.readTimeout = 8000
            val bytes = try {
                require(connection.responseCode == 200)
                connection.inputStream.use { input ->
                    val output = ByteArrayOutputStream()
                    val buffer = ByteArray(8192)
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        require(output.size() + read <= 2_000_000)
                        output.write(buffer, 0, read)
                    }
                    output.toByteArray()
                }
            } finally { connection.disconnect() }
            require(bytes.size <= 2_000_000)
            val raw = bytes.toString(Charsets.UTF_8)
            val packs = parse(raw, true)
            val staged = File(cache.parentFile, cache.name + ".next")
            staged.writeText(raw)
            check(staged.renameTo(cache))
            packs
        }.getOrNull() ?: saved
    }
}

fun catalogImage(path: String): String = if (path.startsWith("/")) "file:///android_asset$path" else path
