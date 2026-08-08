package ai.quangquy.qkeyboard

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.inputmethodservice.InputMethodService
import android.text.InputType
import android.view.HapticFeedbackConstants
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.View
import android.view.inputmethod.EditorInfo
import android.widget.Toast
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import kotlin.concurrent.thread
import kotlin.math.abs
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min

class V04Prefs(context: Context) {
    private val p = context.getSharedPreferences("q_keyboard", Context.MODE_PRIVATE)
    var gatewayUrl: String
        get() = p.getString("gateway_url", "") ?: ""
        set(v) = p.edit().putString("gateway_url", v.trim()).apply()
    var sourceLang: String
        get() = p.getString("source_lang", "vi") ?: "vi"
        set(v) = p.edit().putString("source_lang", v).apply()
    var targetLang: String
        get() = p.getString("target_lang", "en") ?: "en"
        set(v) = p.edit().putString("target_lang", v).apply()
    var keyboardHeight: Int
        get() = p.getInt("keyboard_height", 92)
        set(v) = p.edit().putInt("keyboard_height", v.coerceIn(75, 120)).apply()
    var keyText: Int
        get() = p.getInt("key_text", 100)
        set(v) = p.edit().putInt("key_text", v.coerceIn(80, 125)).apply()
    var gap: Int
        get() = p.getInt("key_gap", 80)
        set(v) = p.edit().putInt("key_gap", v.coerceIn(50, 150)).apply()
    var suggestionCount: Int
        get() = p.getInt("suggestion_count", 3).coerceIn(3, 5)
        set(v) = p.edit().putInt("suggestion_count", v.coerceIn(3, 5)).apply()
    var suggestionText: Int
        get() = p.getInt("suggestion_text", 100)
        set(v) = p.edit().putInt("suggestion_text", v.coerceIn(80, 125)).apply()
    var emojiSize: Int
        get() = p.getInt("emoji_size", 100)
        set(v) = p.edit().putInt("emoji_size", v.coerceIn(80, 130)).apply()
    var contextualEmoji: Boolean
        get() = p.getBoolean("contextual_emoji", true)
        set(v) = p.edit().putBoolean("contextual_emoji", v).apply()
    var personalLearning: Boolean
        get() = p.getBoolean("personal_learning", true)
        set(v) = p.edit().putBoolean("personal_learning", v).apply()
    var commonDictionary: Boolean
        get() = p.getBoolean("community_dictionary", true)
        set(v) = p.edit().putBoolean("community_dictionary", v).apply()
    var haptic: Boolean
        get() = p.getBoolean("haptic", true)
        set(v) = p.edit().putBoolean("haptic", v).apply()
    var showSymbols: Boolean
        get() = p.getBoolean("show_symbols", true)
        set(v) = p.edit().putBoolean("show_symbols", v).apply()
    var shortcuts: String
        get() = p.getString("shortcuts", "qq=Quang Quý AI") ?: ""
        set(v) = p.edit().putString("shortcuts", v).apply()

    fun compactPreset() {
        keyboardHeight = 92; keyText = 100; gap = 80; suggestionCount = 3
        suggestionText = 100; emojiSize = 100; contextualEmoji = true
        haptic = true; showSymbols = true
    }
}

class V04LearningStore(context: Context) {
    private val p = context.getSharedPreferences("q_keyboard_learning_v04", Context.MODE_PRIVATE)
    fun wordCount(word: String) = read("words")[norm(word)] ?: 0
    fun bigramCount(a: String, b: String) = read("bigrams")["${norm(a)}\u0001${norm(b)}"] ?: 0
    fun words(prefix: String) = read("words").filterKeys { it.startsWith(norm(prefix)) }.toList()
    fun next(previous: String): List<Pair<String, Int>> {
        val k = norm(previous) + "\u0001"
        return read("bigrams").filterKeys { it.startsWith(k) }
            .map { it.key.substringAfter('\u0001') to it.value }
    }
    fun record(word: String, previous: String?) {
        val w = norm(word); if (w.isBlank()) return
        val words = read("words").toMutableMap(); words[w] = (words[w] ?: 0) + 1; write("words", words)
        val prev = norm(previous.orEmpty()); if (prev.isBlank()) return
        val bg = read("bigrams").toMutableMap(); val key = "$prev\u0001$w"
        bg[key] = (bg[key] ?: 0) + 1; write("bigrams", bg)
    }
    fun reset() = p.edit().clear().apply()
    private fun norm(s: String) = s.trim().lowercase(Locale.ROOT).trim { !it.isLetterOrDigit() }.take(40)
    private fun read(name: String): Map<String, Int> = runCatching {
        val obj = JSONObject(p.getString(name, "{}") ?: "{}")
        buildMap { val i = obj.keys(); while (i.hasNext()) { val k = i.next(); put(k, obj.optInt(k)) } }
    }.getOrDefault(emptyMap())
    private fun write(name: String, map: Map<String, Int>) {
        val obj = JSONObject(); map.entries.sortedByDescending { it.value }.take(1500).forEach { obj.put(it.key, it.value) }
        p.edit().putString(name, obj.toString()).apply()
    }
}

class V04Predictor(private val prefs: V04Prefs, private val learning: V04LearningStore) {
    private val words = WORDS.trim().split(Regex("\\s+")).map { it.lowercase(Locale.ROOT) }.distinct()
    fun suggest(prefixInput: String, previousInput: String?, count: Int = prefs.suggestionCount): List<String> {
        val prefix = prefixInput.trim().lowercase(Locale.ROOT)
        val previous = previousInput.orEmpty().trim().lowercase(Locale.ROOT)
        val scores = linkedMapOf<String, Int>()
        fun offer(w: String, score: Int) { if (w.isNotBlank() && (scores[w] ?: Int.MIN_VALUE) < score) scores[w] = score }
        if (prefix.isNotBlank()) {
            offer(prefix, 2200)
            NEXT[previous].orEmpty().forEachIndexed { i, w -> if (w.startsWith(prefix)) offer(w, 3300 - i * 55 + learning.bigramCount(previous, w) * 100) }
            if (prefs.personalLearning) learning.words(prefix).forEach { offer(it.first, 2500 + it.second * 60) }
            if (prefs.commonDictionary) words.forEachIndexed { i, w -> if (w.startsWith(prefix) && w != prefix) offer(w, 1800 - min(i, 1400)) }
        } else {
            NEXT[previous].orEmpty().forEachIndexed { i, w -> offer(w, 3000 - i * 60 + learning.bigramCount(previous, w) * 110) }
            if (prefs.personalLearning) learning.next(previous).forEach { offer(it.first, 3500 + it.second * 120) }
            DEFAULTS.forEachIndexed { i, w -> offer(w, 1000 - i * 20) }
        }
        DEFAULTS.forEachIndexed { i, w -> offer(w, 400 - i) }
        return scores.entries.sortedWith(compareByDescending<Map.Entry<String, Int>> { it.value }.thenBy { it.key.length }).map { it.key }.take(count.coerceIn(3, 5))
    }
    fun emoji(context: String): String? {
        if (!prefs.contextualEmoji) return null
        val s = context.lowercase(Locale.ROOT)
        return EMOJI.firstOrNull { it.first.any(s::contains) }?.second
    }
    companion object {
        private val DEFAULTS = listOf("mình", "anh", "em", "không", "có", "được", "và")
        private val NEXT = mapOf(
            "anh" to listOf("có", "muốn", "đang", "thấy", "nghĩ", "cần", "sẽ", "không"),
            "em" to listOf("có", "ơi", "giúp", "thấy", "nghĩ", "được", "nhé", "không"),
            "mình" to listOf("có", "đang", "muốn", "cần", "sẽ", "nên", "không"),
            "tôi" to listOf("có", "muốn", "đang", "cần", "sẽ", "không", "nghĩ"),
            "có" to listOf("thể", "gì", "một", "nhiều", "không", "được", "ai"),
            "không" to listOf("có", "được", "biết", "phải", "nên", "sao", "thể"),
            "muốn" to listOf("làm", "tạo", "biết", "hỏi", "dùng", "được", "thêm"),
            "cần" to listOf("làm", "thêm", "biết", "dùng", "một", "được", "hỗ trợ"),
            "đang" to listOf("làm", "dùng", "ở", "có", "tìm", "chờ", "học"),
            "hôm" to listOf("nay", "qua", "trước"), "ngày" to listOf("mai", "hôm", "này", "mới"),
            "xin" to listOf("chào", "cảm", "lỗi", "phép"), "cảm" to listOf("ơn", "giác", "thấy"),
            "chúc" to listOf("mừng", "bạn", "anh", "em", "mọi người"),
            "viết" to listOf("lại", "bài", "nội dung", "giúp", "cho"),
            "dịch" to listOf("sang", "tiếng", "đoạn", "này", "giúp"),
            "facebook" to listOf("bài", "nhóm", "comment", "có", "đang"),
            "marketing" to listOf("AI", "online", "automation", "content", "manager"),
            "quang" to listOf("quý"), "quý" to listOf("AI", "ơi", "nguyễn")
        )
        private val EMOJI = listOf(
            listOf("sinh nhật", "birthday") to "🎂", listOf("chúc mừng") to "🎉", listOf("yêu", "thương", "love") to "❤️",
            listOf("haha", "hihi", "cười", "vui") to "😂", listOf("ok", "okay", "đồng ý", "được rồi") to "👍",
            listOf("cảm ơn", "thank") to "🙏", listOf("buồn", "sad") to "😢", listOf("giận", "tức") to "😡",
            listOf("ngon", "ăn") to "😋", listOf("ngủ") to "😴", listOf("hot", "cháy", "đỉnh") to "🔥",
            listOf("tiền", "lương", "doanh thu") to "💰", listOf("cà phê", "coffee") to "☕", listOf("xe") to "🚗",
            listOf("máy bay") to "✈️", listOf("bóng đá") to "⚽", listOf("trí tuệ nhân tạo", "chatbot", " ai ") to "🤖",
            listOf("ý tưởng", "idea") to "💡", listOf("công việc", "làm việc") to "💼"
        )
        private const val WORDS = """
            là và có của một không được cho trong với này đó các người tôi bạn anh em mình chúng ta họ khi đã đang sẽ rất cũng còn như nhưng nếu thì vì để từ trên dưới vào ra về lại hơn nhất nhiều ít mới cũ tốt đẹp hay đúng sai cần muốn biết thấy nghĩ nói làm dùng tạo thêm sửa đổi chọn xem hỏi trả lời giúp hỗ trợ nhanh chậm dễ khó lớn nhỏ cao thấp gần xa trước sau hôm nay ngày mai hôm qua giờ phút tuần tháng năm sáng trưa chiều tối đêm nhà trường công ty cửa hàng khách hàng sản phẩm dịch vụ giá tiền lương doanh thu chi phí công việc dự án kế hoạch mục tiêu kết quả thông tin nội dung bài viết hình ảnh video âm thanh tin nhắn email điện thoại máy tính website ứng dụng tài khoản mật khẩu cài đặt bàn phím ngôn ngữ tiếng Việt Anh Nhật Trung Hàn dịch phiên dịch viết lại sửa lỗi chính tả ngữ pháp câu từ từ vựng gợi ý dự đoán học tự động thông minh dữ liệu riêng tư bảo mật an toàn mạng internet online offline tải lưu mở đóng bật tắt tăng giảm chọn lựa tùy chỉnh giao diện màu sắc chủ đề phím hàng số ký tự biểu tượng emoji icon cảm xúc vui buồn yêu thích cảm ơn xin chào xin lỗi chúc mừng sinh nhật ngủ ngon buổi gặp hẹn khỏe sao rồi nhé nha nè á ạ ơi vậy hả ha haha hihi dạ vâng ừ uh um oke hello hi bye thanks sorry please yes no maybe love like wow cool nice great perfect amazing beautiful cute happy sad angry tired busy free ready done start stop next back home menu settings translate chat copy paste clipboard note shortcut keyboard language Vietnamese English Japanese Chinese Korean Facebook Messenger Instagram TikTok YouTube Google ChatGPT Gemini OpenAI AI chatbot automation marketing content comment bình luận caption post nhóm trang cá nhân fanpage quảng cáo chiến dịch thương hiệu lead sale bán hàng mua hàng đơn hàng giao hàng thanh toán ngân hàng chuyển khoản hóa đơn hợp đồng báo giá khuyến mãi ưu đãi spa mỹ phẩm bất động sản nhà đất xe công nghệ phần mềm code lập trình API server cloud GitHub Make n8n Telegram Notion Drive Sheets tài liệu file PDF Word Excel camera micro giọng nói cuộc gọi nhạc phim trò chơi bóng đá du lịch ăn uống cà phê nhà hàng khách sạn sân bay xe máy ô tô đường phố thành phố Việt Nam Hà Nội Sài Gòn Hồ Chí Minh Đà Nẵng Quảng Ngãi gia đình ba mẹ cha mẹ anh chị con bạn bè đồng nghiệp sếp nhân viên đội nhóm học sinh sinh viên giáo viên đối tác cộng đồng mọi người ai cái gì tại sao khi nào ở đâu bao nhiêu thế nào hiện tại sau này tương lai thường xuyên đôi khi luôn luôn chưa từng lần đầu tiếp theo cuối cùng bắt đầu kết thúc mở rộng giới hạn miễn phí trả phí đăng ký đăng nhập đăng xuất cập nhật phiên bản test thử lỗi ổn định mượt lag chuyên nghiệp lịch sự thân thiện tự nhiên ngắn gọn chi tiết đầy đủ chính xác phù hợp liên quan
        """
    }
}

class V04AiGateway(private val prefs: V04Prefs) {
    fun ask(text: String, done: (Result<String>) -> Unit) {
        if (prefs.gatewayUrl.isBlank()) { done(Result.failure(IllegalStateException("Chưa cấu hình AI Gateway"))); return }
        thread {
            runCatching {
                val c = URL(prefs.gatewayUrl).openConnection() as HttpURLConnection
                c.requestMethod = "POST"; c.connectTimeout = 10000; c.readTimeout = 30000; c.doOutput = true
                c.setRequestProperty("Content-Type", "application/json")
                c.outputStream.use { it.write(JSONObject().put("action", "chat").put("text", text).toString().toByteArray()) }
                val body = (if (c.responseCode in 200..299) c.inputStream else c.errorStream).bufferedReader().use { it.readText() }
                if (c.responseCode !in 200..299) error("HTTP ${c.responseCode}")
                JSONObject(body).optString("text").ifBlank { error("Gateway không trả text") }
            }.also(done)
        }
    }
}

class QAiKeyV04View(context: Context, private val prefs: V04Prefs, private val listener: Listener) : View(context) {
    interface Listener {
        fun key(s: String); fun backspace(); fun enter(); fun space(); fun action(s: String); fun suggestion(s: String); fun reference(s: String); fun emoji(s: String)
    }
    data class Target(val rect: RectF, val value: String)
    private val p = Paint(Paint.ANTI_ALIAS_FLAG)
    private val bg = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(242, 244, 249) }
    private val keyBg = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE }
    private val refBg = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE }
    private val divider = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.rgb(220, 223, 230); strokeWidth = 1f }
    private val keys = mutableListOf<Target>(); private val tools = mutableListOf<Target>(); private val emojis = mutableListOf<Target>()
    var suggestions: List<String> = listOf("mình", "anh", "em"); var contextualEmoji: String? = null
    private var mode = "suggest"; private var referenceText: String? = null; private var sugScroll = 0f; private var toolScroll = 0f
    private var downX = 0f; private var lastX = 0f; private var dragging = false; private var category = 0
    fun suggestionsMode() { mode = "suggest"; invalidate() }; fun toolsMode() { mode = "tools"; invalidate() }; fun emojiMode() { mode = "emoji"; invalidate() }
    fun setReference(s: String?) { referenceText = s?.takeIf { it.isNotBlank() }; requestLayout(); invalidate() }
    override fun onMeasure(w: Int, h: Int) { setMeasuredDimension(MeasureSpec.getSize(w), (300f * prefs.keyboardHeight / 100f * resources.displayMetrics.density).toInt()) }
    override fun onDraw(c: Canvas) {
        c.drawColor(bg.color); keys.clear(); tools.clear(); emojis.clear(); val d = resources.displayMetrics.density
        val refH = if (referenceText != null) 40f * d else 0f; val barH = 46f * d
        if (referenceText != null) drawReference(c, refH)
        if (mode == "emoji") { drawEmojiBar(c, refH, barH); drawEmojiGrid(c, refH + barH) }
        else { if (mode == "tools") drawTools(c, refH, barH) else drawSuggestions(c, refH, barH); drawKeys(c, refH + barH) }
    }
    private fun drawReference(c: Canvas, h: Float) {
        val d = resources.displayMetrics.density; val pad = 5f * d; val r = RectF(pad, 3f*d, width-pad, h-2f*d); c.drawRoundRect(r, 9f*d, 9f*d, refBg)
        val aw = 34f*d; val rs = width-pad-aw*3; p.color=Color.rgb(45,45,50); p.textAlign=Paint.Align.LEFT; p.textSize=13f*d
        c.drawText(ellipsis(referenceText.orEmpty().replace('\n',' '), rs-20f*d), 12f*d, h/2+5f*d, p)
        p.textAlign=Paint.Align.CENTER; p.textSize=19f*d; listOf("↳","↻","⧉").forEachIndexed { i,s -> c.drawText(s, rs+aw*(i+.5f), h/2+6f*d,p) }
    }
    private fun drawSuggestions(c: Canvas, top: Float, h: Float) {
        val d=resources.displayMetrics.density; val menu=48f*d; val emo=44f*d; val left=menu; val right=width-emo; val area=right-left; val n=prefs.suggestionCount
        val slot=if(n<=3) area/n else max(94f*d,area/3f); val maxScroll=max(0f,slot*n-area); sugScroll=sugScroll.coerceIn(0f,maxScroll)
        p.color=Color.rgb(42,42,48);p.textAlign=Paint.Align.CENTER;p.textSize=21f*d;c.drawText("☰",menu/2,top+h/2+7f*d,p);tools+=Target(RectF(0f,top,menu,top+h),"menu")
        c.save();c.clipRect(left,top,right,top+h)
        suggestions.take(n).forEachIndexed { i,s -> val x=left+i*slot-sugScroll;val r=RectF(x,top,x+slot,top+h);drawSuggestion(c,r,s);tools+=Target(r,"s:$i");if(i>0)c.drawLine(x,top+9f*d,x,top+h-9f*d,divider) }
        c.restore();contextualEmoji?.let { p.textSize=23f*d*prefs.emojiSize/100f;c.drawText(it,width-emo/2,top+h/2+8f*d,p);tools+=Target(RectF(right,top,width.toFloat(),top+h),"ctx") }
    }
    private fun drawSuggestion(c:Canvas,r:RectF,s:String){val d=resources.displayMetrics.density;p.color=Color.rgb(42,42,48);p.textAlign=Paint.Align.CENTER;p.textSize=14f*d*prefs.suggestionText/100f;val maxW=r.width()-16f*d;val t=s.replace('\n',' ').trim();if(t.isBlank())return;if(p.measureText(t)<=maxW){c.drawText(t,r.centerX(),r.centerY()+p.textSize*.34f,p);return};val words=t.split(Regex("\\s+"));var l1="";var used=0;for((i,w)in words.withIndex()){val q=if(l1.isBlank())w else "$l1 $w";if(p.measureText(q)<=maxW){l1=q;used=i+1}else break};if(used==0){c.drawText(ellipsis(t,maxW),r.centerX(),r.centerY()+p.textSize*.34f,p);return};val l2=ellipsis(words.drop(used).joinToString(" "),maxW);val gap=p.textSize*1.02f;c.drawText(l1,r.centerX(),r.centerY()-.08f*gap,p);if(l2.isNotBlank())c.drawText(l2,r.centerX(),r.centerY()+.92f*gap,p)}
    private fun drawTools(c:Canvas,top:Float,h:Float){val d=resources.displayMetrics.density;val list=listOf("back" to "‹","translate" to "🌐","chat" to "AI","clipboard" to "📋","emoji" to "☺","settings" to "⚙");val slot=66f*d;toolScroll=toolScroll.coerceIn(0f,max(0f,slot*list.size-width));c.save();c.clipRect(0f,top,width.toFloat(),top+h);list.forEachIndexed{i,it->val r=RectF(i*slot-toolScroll,top,(i+1)*slot-toolScroll,top+h);p.color=Color.rgb(40,40,45);p.textAlign=Paint.Align.CENTER;p.textSize=if(it.second=="AI")15f*d else 20f*d;c.drawText(it.second,r.centerX(),top+h/2+7f*d,p);tools+=Target(r,it.first)};c.restore()}
    private fun drawKeys(c:Canvas,start:Float){val d=resources.displayMetrics.density;val rows=listOf(listOf("1","2","3","4","5","6","7","8","9","0"),listOf("q","w","e","r","t","y","u","i","o","p"),listOf("a","s","d","f","g","h","j","k","l"),listOf("⇧","z","x","c","v","b","n","m","⌫"));val sec=mapOf("a" to "@","s" to "#","d" to "$","f" to "%","g" to "-","h" to "+","j" to "(","k" to ")","l" to "'","z" to "*","x" to "\"","c" to "/","v" to ":","b" to ";","n" to "!","m" to "?");val gap=3f*d*prefs.gap/100f;val side=5f*d;val rowH=(height-start-4f*d)/5f;var y=start
        rows.forEachIndexed{ri,row->val indent=if(ri==2)18f*d else 0f;val kw=(width-side*2-indent*2-gap*(row.size-1))/row.size;var x=side+indent;row.forEach{v->val r=RectF(x,y,x+kw,y+rowH-gap);drawKey(c,r,v.uppercase(),if(prefs.showSymbols&&ri>0)sec[v] else null,rowH);keys+=Target(r,v);x+=kw+gap};y+=rowH}
        val bottom=listOf("?123","VI",",","SPACE","☺",".","↵");val weights=listOf(1.05f,.72f,.58f,3.25f,.72f,.58f,1f);val aw=width-side*2-gap*(bottom.size-1);val total=weights.sum();var x=side;bottom.indices.forEach{i->val kw=aw*weights[i]/total;val r=RectF(x,y,x+kw,y+rowH-gap);drawKey(c,r,if(bottom[i]=="SPACE")"Tiếng Việt" else bottom[i],null,rowH);keys+=Target(r,bottom[i]);x+=kw+gap}}
    private fun drawKey(c:Canvas,r:RectF,label:String,small:String?,rowH:Float){val d=resources.displayMetrics.density;c.drawRoundRect(r,7f*d,7f*d,keyBg);p.color=Color.BLACK;p.textAlign=Paint.Align.CENTER;p.textSize=(if(label.length>2)13f else 23f)*d*prefs.keyText/100f;c.drawText(label,r.centerX(),r.centerY()+p.textSize*.33f,p);if(small!=null){p.textSize=9.5f*d;p.color=Color.DKGRAY;c.drawText(small,r.centerX()+r.width()*.23f,r.top+rowH*.22f,p)}}
    private fun drawEmojiBar(c:Canvas,top:Float,h:Float){val d=resources.displayMetrics.density;val back=44f*d;p.color=Color.rgb(40,40,45);p.textAlign=Paint.Align.CENTER;p.textSize=22f*d;c.drawText("‹",back/2,top+h/2+8f*d,p);tools+=Target(RectF(0f,top,back,top+h),"back");val slot=(width-back)/CATS.size;CATS.forEachIndexed{i,cat->val r=RectF(back+i*slot,top,back+(i+1)*slot,top+h);p.textSize=18f*d;p.alpha=if(i==category)255 else 130;c.drawText(cat.first,r.centerX(),top+h/2+6f*d,p);p.alpha=255;tools+=Target(r,"cat:$i")}}
    private fun drawEmojiGrid(c:Canvas,start:Float){val d=resources.displayMetrics.density;val list=CATS[category].second;val cols=7;val rows=5;val cw=width/cols.toFloat();val ch=(height-start)/rows;p.textAlign=Paint.Align.CENTER;p.textSize=24f*d*prefs.emojiSize/100f;list.take(cols*rows).forEachIndexed{i,e->val col=i%cols;val row=i/cols;val r=RectF(col*cw,start+row*ch,(col+1)*cw,start+(row+1)*ch);c.drawText(e,r.centerX(),r.centerY()+p.textSize*.33f,p);emojis+=Target(r,e)}}
    override fun onTouchEvent(e:MotionEvent):Boolean{val d=resources.displayMetrics.density;val refH=if(referenceText!=null)40f*d else 0f;val barH=46f*d;when(e.action){MotionEvent.ACTION_DOWN->{downX=e.x;lastX=e.x;dragging=false;return true};MotionEvent.ACTION_MOVE->{if(e.y in refH..(refH+barH)&&mode!="emoji"){val dx=e.x-lastX;if(abs(e.x-downX)>8f*d)dragging=true;if(mode=="suggest"&&prefs.suggestionCount>3){val area=width-92f*d;val slot=max(94f*d,area/3f);sugScroll=(sugScroll-dx).coerceIn(0f,max(0f,slot*prefs.suggestionCount-area))}else if(mode=="tools")toolScroll=(toolScroll-dx).coerceIn(0f,max(0f,66f*d*6-width));lastX=e.x;invalidate()};return true};MotionEvent.ACTION_UP->{if(prefs.haptic)performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP);if(dragging)return true;if(referenceText!=null&&e.y<refH){val aw=34f*d;val rs=width-5f*d-aw*3;if(e.x>=rs)listener.reference(listOf("insert","replace","copy")[floor((e.x-rs)/aw).toInt().coerceIn(0,2)])else listener.reference("insert");return true};if(e.y in refH..(refH+barH)){tools.lastOrNull{it.rect.contains(e.x,e.y)}?.let{t->when{t.value.startsWith("s:")->suggestions.getOrNull(t.value.substringAfter(':').toIntOrNull()?:-1)?.let(listener::suggestion);t.value=="ctx"->contextualEmoji?.let(listener::emoji);t.value.startsWith("cat:")->{category=(t.value.substringAfter(':').toIntOrNull()?:0).coerceIn(0,CATS.lastIndex);invalidate()};else->listener.action(t.value)}};return true};if(mode=="emoji"){emojis.firstOrNull{it.rect.contains(e.x,e.y)}?.let{listener.emoji(it.value)};return true};keys.firstOrNull{it.rect.contains(e.x,e.y)}?.let{when(it.value){"⌫"->listener.backspace();"↵"->listener.enter();"SPACE"->listener.space();"☺"->listener.action("emoji");"⇧","?123","VI"->Unit;else->listener.key(it.value)}};return true}};return true}
    private fun ellipsis(s:String,maxW:Float):String{if(s.isBlank())return "";if(p.measureText(s)<=maxW)return s;val ell="…";val n=p.breakText(s,true,max(1f,maxW-p.measureText(ell)),null).coerceAtLeast(1).coerceAtMost(s.length);return s.take(n).trimEnd()+ell}
    companion object { private val CATS=listOf(
        "😀" to listOf("😀","😃","😄","😁","😆","😅","😂","🤣","😊","😇","🙂","🙃","😉","😍","🥰","😘","😋","😛","😜","🤪","🤨","🧐","🤓","😎","🥳","😏","😒","😞","😔","😢","😭","😡","🤯","😴","🤤"),
        "❤️" to listOf("❤️","🧡","💛","💚","💙","💜","🖤","🤍","🤎","💔","❣️","💕","💞","💓","💗","💖","💘","💝","💟","♥️","💌","🌹","💐","🌷","🌸","✨","⭐","🌟","💫","🔥","🎉","🎊","🎂","🎁","🥂"),
        "👍" to listOf("👍","👎","👌","✌️","🤞","🤟","🤘","🤙","👈","👉","👆","👇","☝️","✋","🤚","🖐️","🖖","👋","👏","🙌","👐","🤲","🙏","✍️","💪","🫶","🤝","👀","🧠","🗣️","👤","👥","💅","🤳","🫰","🫡"),
        "🎉" to listOf("🎉","🎊","🎈","🎁","🎂","🥳","🏆","🥇","🥈","🥉","⚽","🏀","🏈","⚾","🎾","🏐","🎱","🏓","🏸","🥊","🎯","🎮","🎲","🎸","🎹","🎤","🎧","🎬","📸","🎨","🎭","🎪","🚀","✨","🔥"),
        "🍔" to listOf("🍔","🍟","🍕","🌭","🥪","🌮","🍜","🍝","🍚","🍣","🍤","🍗","🥩","🥗","🍲","🍱","🥟","🍩","🍪","🎂","🍰","🍫","🍬","🍭","🍎","🍊","🍋","🍉","🍇","🍓","🥭","☕","🧋","🍺","🥂"),
        "🚗" to listOf("🚗","🚕","🚌","🚎","🏎️","🚓","🚑","🚒","🚐","🛻","🏍️","🚲","✈️","🚀","🚁","🚂","🚆","🚇","🚢","⛵","🗺️","🏠","🏢","🏨","🏖️","🏝️","⛰️","🌋","🌇","🌃","🌍","🌎","🌏","📍","🧭"),
        "💡" to listOf("💡","🤖","💻","⌨️","🖥️","📱","📲","💾","💿","🔋","🔌","⚙️","🛠️","🔧","🔑","🔒","🔓","📌","📎","✂️","📝","📋","📚","📖","📊","📈","📉","💼","📁","🗂️","📧","💬","🔔","⏰","✅") ) }
}

class QAiKeyV04Service : InputMethodService(), QAiKeyV04View.Listener {
    private lateinit var view:QAiKeyV04View;private lateinit var prefs:V04Prefs;private lateinit var store:V04LearningStore;private lateinit var predictor:V04Predictor;private lateinit var translator:TranslationManager;private lateinit var ai:V04AiGateway
    private val telex=TelexEngine();private var composing="";private var translated:String?=null;private var lastContext="";private var aiCandidate:String?=null;private var sensitive=false
    override fun onCreate(){super.onCreate();prefs=V04Prefs(this);store=V04LearningStore(this);predictor=V04Predictor(prefs,store);translator=TranslationManager(this);ai=V04AiGateway(prefs)}
    override fun onCreateInputView():View{view=QAiKeyV04View(this,prefs,this);refresh("");return view}
    override fun onStartInput(a:EditorInfo?,r:Boolean){super.onStartInput(a,r);telex.reset();composing="";translated=null;lastContext="";aiCandidate=null;sensitive=isSensitive(a?.inputType?:0);if(::view.isInitialized){view.setReference(null);refresh("");view.suggestionsMode()}}
    override fun key(s:String){if(s.length==1&&s[0].isLetter()){composing=telex.push(s[0]);currentInputConnection.setComposingText(composing,1);refresh(composing);view.suggestionsMode()}else{commit();currentInputConnection.commitText(s,1);refresh("")}}
    override fun backspace(){if(telex.currentRaw().isNotEmpty()){composing=telex.backspace();currentInputConnection.setComposingText(composing,1);refresh(composing)}else{currentInputConnection.deleteSurroundingText(1,0);refresh("")};view.suggestionsMode()}
    override fun space(){val prev=previous();val word=composing;val exp=expand(composing);if(exp!=null)currentInputConnection.setComposingText(exp,1);commit();currentInputConnection.commitText(" ",1);if(!sensitive&&prefs.personalLearning&&word.isNotBlank())store.record(word,prev);refresh("");view.suggestionsMode()}
    override fun enter(){val prev=previous();val word=composing;commit();if(!sensitive&&prefs.personalLearning&&word.isNotBlank())store.record(word,prev);currentInputConnection.sendKeyEvent(KeyEvent(KeyEvent.ACTION_DOWN,KeyEvent.KEYCODE_ENTER));currentInputConnection.sendKeyEvent(KeyEvent(KeyEvent.ACTION_UP,KeyEvent.KEYCODE_ENTER));refresh("")}
    override fun action(s:String){when(s){"menu"->view.toolsMode();"back"->{view.setReference(null);view.suggestionsMode()};"translate"->if(sensitive)toast("Dịch đã tắt trong ô mật khẩu/PIN")else translate(context());"chat"->if(sensitive)toast("AI đã tắt trong ô mật khẩu/PIN")else chat();"clipboard"->pasteClipboard();"emoji"->view.emojiMode();"settings"->startActivity(Intent(this,V04SettingsActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))}}
    override fun suggestion(s:String){if(s.isBlank())return;aiCandidate?.let{if(s==compact(it)){commit();currentInputConnection.commitText(it,1);aiCandidate=null;refresh("");return}};val prev=previous();if(telex.currentRaw().isNotEmpty()){currentInputConnection.setComposingText(s,1);currentInputConnection.finishComposingText();telex.reset();composing=""}else currentInputConnection.commitText(s,1);currentInputConnection.commitText(" ",1);if(!sensitive&&prefs.personalLearning)store.record(s.substringBefore(' '),prev);refresh("");view.suggestionsMode()}
    override fun emoji(s:String){commit();currentInputConnection.commitText(s,1);refresh("");view.suggestionsMode()}
    override fun reference(s:String){val cand=translated?:return;when(s){"copy"->{copy(cand);toast("Đã sao chép")};"replace"->{val selected=currentInputConnection.getSelectedText(0)?.toString().orEmpty();if(selected.isNotBlank())currentInputConnection.commitText(cand,1)else{if(lastContext.isNotBlank())currentInputConnection.deleteSurroundingText(lastContext.length,0);currentInputConnection.commitText(cand,1)};finishCandidate()};else->{currentInputConnection.commitText(cand,1);finishCandidate()}}}
    private fun refresh(prefix:String){if(!::view.isInitialized)return;val prev=previous();view.suggestions=predictor.suggest(prefix,prev);view.contextualEmoji=predictor.emoji("$prev $prefix");view.invalidate()}
    private fun previous():String{val before=currentInputConnection?.getTextBeforeCursor(140,0)?.toString().orEmpty();val cleaned=if(composing.isNotBlank()&&before.endsWith(composing))before.dropLast(composing.length)else before;return cleaned.trimEnd().split(Regex("\\s+")).lastOrNull().orEmpty().trim{!it.isLetterOrDigit()}.lowercase(Locale.ROOT)}
    private fun translate(input:String){commit();val text=input.trim();if(text.isBlank()){toast("Chọn hoặc gõ đoạn cần dịch trước");return};lastContext=text;view.setReference("${prefs.sourceLang.uppercase()} → ${prefs.targetLang.uppercase()} • Đang dịch…");view.suggestionsMode();translator.translate(text,prefs.sourceLang,prefs.targetLang){r->view.post{r.onSuccess{translated=it;view.setReference(it)}.onFailure{view.setReference(null);toast("Không dịch được: ${it.message}")}}}}
    private fun chat(){commit();val text=context().trim();if(text.isBlank()){toast("Chọn hoặc gõ nội dung trước rồi bấm AI");return};lastContext=text;view.suggestions=listOf("AI đang xử lý…");view.contextualEmoji="🤖";view.suggestionsMode();ai.ask("Hãy hiểu ngữ cảnh và trả lời hoặc xử lý nội dung sau một cách hữu ích, tự nhiên, ngắn gọn. Chỉ trả về nội dung cần chèn:\n$text"){r->view.post{r.onSuccess{aiCandidate=it;view.suggestions=listOf(compact(it));view.contextualEmoji="🤖";view.suggestionsMode()}.onFailure{toast(it.message?:"AI lỗi");refresh("")}}}}
    private fun context():String{commit();val selected=currentInputConnection.getSelectedText(0)?.toString().orEmpty().trim();if(selected.isNotBlank())return selected;val before=currentInputConnection.getTextBeforeCursor(800,0)?.toString().orEmpty();return before.substringAfterLast('\n').substringAfterLast('.').substringAfterLast('!').substringAfterLast('?').trim()}
    private fun pasteClipboard(){val cm=getSystemService(Context.CLIPBOARD_SERVICE)as ClipboardManager;val t=cm.primaryClip?.getItemAt(0)?.coerceToText(this)?.toString().orEmpty();if(t.isBlank())toast("Clipboard đang trống")else{commit();currentInputConnection.commitText(t,1);refresh("")};view.suggestionsMode()}
    private fun expand(v:String):String?=prefs.shortcuts.lines().mapNotNull{val i=it.indexOf('=');if(i<=0)null else it.substring(0,i).trim() to it.substring(i+1)}.firstOrNull{it.first==v}?.second
    private fun commit(){if(telex.currentRaw().isNotEmpty()){currentInputConnection.finishComposingText();telex.reset();composing=""}}
    private fun finishCandidate(){translated=null;lastContext="";view.setReference(null);refresh("");view.suggestionsMode()}
    private fun copy(t:String){(getSystemService(Context.CLIPBOARD_SERVICE)as ClipboardManager).setPrimaryClip(ClipData.newPlainText("Q Ai Key v04",t))}
    private fun compact(s:String,max:Int=28)=s.replace('\n',' ').let{if(it.length<=max)it else it.take(max-1)+"…"}
    private fun isSensitive(t:Int):Boolean{val c=t and InputType.TYPE_MASK_CLASS;val v=t and InputType.TYPE_MASK_VARIATION;return(c==InputType.TYPE_CLASS_TEXT&&v in setOf(InputType.TYPE_TEXT_VARIATION_PASSWORD,InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD,InputType.TYPE_TEXT_VARIATION_WEB_PASSWORD))||(c==InputType.TYPE_CLASS_NUMBER&&v==InputType.TYPE_NUMBER_VARIATION_PASSWORD)}
    private fun toast(s:String)=Toast.makeText(this,s,Toast.LENGTH_SHORT).show()
}
