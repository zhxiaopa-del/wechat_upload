import os
import re
import time
import json
import tempfile
import requests
from openai import OpenAI
from duckduckgo_search import DDGS
import feedparser
import paramiko

# ================= 配置区域 =================
LLM_CONFIG = {
    "api_key": "sk-ac445b11dbe74063b5a9d379d773fec4",
    "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "model_name": "qwen-plus",
    "fallback_models": ["qwen-plus", "qwen-max"],
}

# WECHAT_CONFIG = {
#     "app_id": "wxf2f49eb8e5b48095",
#     "app_secret": "58ca753a556057b6f2ba0a59832e9c9c",
# }
# 公众号: 怪怪科技说
# AppID: wx542d7b121573768d
# AppSecret: 41bed59634b2a610db4f6b8a416a58dd
WECHAT_CONFIG = {
    "app_id": "wx542d7b121573768d",
    "app_secret": "41bed59634b2a610db4f6b8a416a58dd",
}
SSH_CONFIG = {
    "host": os.environ.get("SSH_HOST", "123.57.236.249"),
    "port": int(os.environ.get("SSH_PORT", 22)),
    "username": os.environ.get("SSH_USER", "root"),
    "password": os.environ.get("SSH_PASS", "xia@yitiao123"),
}

SEARCH_TOPIC = """
AI 大模型 GPT OpenAI DeepSeek Claude Gemini
人工智能 突破 发布 融资
自动驾驶 芯片 算力 GPU
机器人 AGI
科技 巨头 苹果 谷歌 微软 Meta 亚马逊
"""
keywords = [
    # 🔥 大模型 / AI 核心
    "AI", "人工智能", "大模型", "GPT", "OpenAI", "DeepSeek", "Claude", "Gemini",

    # 🚀 行业动态
    "发布", "突破", "融资", "收购", "开源",

    # 🧠 技术方向
    "AGI", "机器人", "自动驾驶",

    # 💻 硬件 / 算力
    "芯片", "GPU", "算力", "NVIDIA", "英伟达",

    # 🏢 科技巨头
    "苹果", "Apple",
    "谷歌", "Google",
    "微软", "Microsoft",
    "Meta", "亚马逊", "Amazon"
]
AUTHOR='张小爬'
# ===========================================


class WeChatAIAgent:
    def __init__(self):
        self.client = OpenAI(
            api_key=LLM_CONFIG["api_key"],
            base_url=LLM_CONFIG["base_url"]
        )
        self.wechat_token = None
        self.token_expire_time = 0
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    # ==================== 搜索 ====================
    def search_news(self):
        import datetime

        print("📡 [1/6] 正在读取科技媒体 RSS 源...")

        # rss_sources = [
        #     "https://www.jiqizhixin.com/rss",
        #     "https://www.qbitai.com/feed",
        #     "https://www.36kr.com/feed",
        #     "https://www.ifanr.com/feed",
        #     "https://techcrunch.com/category/artificial-intelligence/feed/",
        #     "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
        #     "https://venturebeat.com/category/ai/feed/",
        #     "https://www.wired.com/feed/category/science/latest/rss",
        #     "https://arstechnica.com/feed/",
        #     "https://openai.com/news/rss.xml",
        #     "https://deepmind.google/blog/rss.xml",
        #     "https://arxiv.org/rss/cs.AI",
        #     "https://arxiv.org/rss/cs.CL",
            
        # ]
        rss_sources = [
            # =========================
            # 🇨🇳 中文 AI 媒体（更新最快）
            # =========================

            "https://arxiv.org/rss/cs.CL",
            "https://www.jiqizhixin.com/rss",          # 机器之心 - 国内AI第一媒体
            "https://www.qbitai.com/feed",             # 量子位 - 日更多篇
            "https://www.36kr.com/feed",               # 36氪 - 科技创投
            "https://www.ifanr.com/feed",              # 爱范儿 - 科技消费
            "https://www.tmtpost.com/rss",             # 钛媒体 - 科技商业
            "https://www.pingwest.com/rss",            # 品玩 - 科技快讯
            "https://www.geekpark.net/rss",            # 极客公园 - 产品趋势

            # =========================
            # 🌍 英文 AI 主流媒体（日更）
            # =========================
            "https://techcrunch.com/category/artificial-intelligence/feed/",
            "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
            "https://venturebeat.com/category/ai/feed/",
            "https://arstechnica.com/feed/",

            # =========================
            # 🏢 AI 公司官方博客
            # =========================
            "https://openai.com/news/rss.xml",
            "https://deepmind.google/blog/rss.xml",
            "https://ai.googleblog.com/feeds/posts/default",

            # =========================
            # 🔬 AI 论文 & 研究
            # =========================
            "https://arxiv.org/rss/cs.AI",
            "https://arxiv.org/rss/cs.CL",
            "https://paperswithcode.com/rss",
            "https://www.marktechpost.com/feed/",

            # =========================
            # 🛠️ AI 工具 & 产品发现
            # =========================
            "https://theresanaiforthat.com/rss",
            "https://www.futuretools.io/rss",

            # =========================
            # 👨‍💻 AI 开发社区
            # =========================
            "https://dev.to/feed/tag/ai",
            "https://www.reddit.com/r/LocalLLaMA/.rss",

            # =========================
            # ☁️ 云厂商 AI 博客
            # =========================
            "https://aws.amazon.com/blogs/machine-learning/feed/",

            # =========================
            # 💰 创投 & 商业
            # =========================
            "https://sifted.eu/feed/",
        ]

        today = datetime.datetime.utcnow().date()
        seen_titles = set()
        candidates = []

        for url in rss_sources:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:5]:
                    title = entry.title
                    link = entry.link

                    # 👉 去重
                    if title in seen_titles:
                        continue
                    seen_titles.add(title)

                    # 👉 时间过滤
                    published = entry.get("published_parsed")
                    if published:
                        pub_date = datetime.date(
                            published.tm_year,
                            published.tm_mon,
                            published.tm_mday
                        )
                        if (today - pub_date).days > 1:
                            continue

                    # 👉 关键词过滤
                    if any(k.lower() in title.lower() for k in keywords):
                        candidates.append({
                            "title": title,
                            "href": link,
                            "summary": entry.get("summary", "")
                        })

            except Exception as e:
                print(f"   ⚠️ 读取源 {url} 失败: {e}")
                continue

        if not candidates:
            print("   ⚠️ RSS 无结果，启用远程搜索...")
            candidates = self._search_via_ssh()

        print(f"   ✅ 获取 {len(candidates)} 条有效资讯")
        return candidates[:5]

    def _search_via_ssh(self):
        ssh = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=SSH_CONFIG["host"], port=SSH_CONFIG["port"],
                username=SSH_CONFIG["username"], password=SSH_CONFIG["password"],
                timeout=10,
            )
            search_script = (
                'python3 -c "'
                "from duckduckgo_search import DDGS;"
                "import json;"
                f"results = list(DDGS().news('{SEARCH_TOPIC}', max_results=3));"
                "print(json.dumps(results, ensure_ascii=False))"
                '"'
            )
            stdin, stdout, stderr = ssh.exec_command(search_script, timeout=30)
            output = stdout.read().decode("utf-8", errors="ignore").strip()
            if output:
                results = json.loads(output)
                return [{"title": r.get("title", ""), "href": r.get("url", r.get("href", "")), "summary": r.get("body", "")} for r in results]
        except Exception as e:
            print(f"   ⚠️ [SSH] 远程搜索失败: {e}")
        finally:
            if ssh:
                ssh.close()
        return []

    # ==================== 抓取网页 ====================
    def fetch_content(self, url):
        """抓取网页文本内容，同时提取原文中的图片 URL 存到 self._original_images"""
        print(f"📖 [2/6] 正在阅读原文: {url}")
        self._original_images = []

        # 方案 A: Jina Reader（纯文本，无法提取图片，但内容质量好）
        try:
            jina_url = f"https://r.jina.ai/{url}"
            resp = requests.get(jina_url, timeout=30)
            if resp.status_code == 200 and len(resp.text) > 100:
                print("   ✅ [Jina] 读取成功")
                self._extract_images_from_url(url)
                return resp.text[:12000]
        except Exception as e:
            print(f"   ⚠️ [Jina] 失败: {e}，尝试远程服务器...")

        # 方案 B: SSH
        remote_text = self._fetch_via_ssh(url)
        if remote_text:
            self._extract_images_from_html(remote_text, url)
            return remote_text

        # 方案 C: 本地 BeautifulSoup
        try:
            print("   🔄 [Local] 正在尝试本地直接抓取...")
            resp = requests.get(url, headers=self.headers, timeout=15)
            resp.encoding = resp.apparent_encoding
            if resp.status_code == 200:
                self._extract_images_from_html(resp.text, url)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.extract()
                text = soup.get_text(separator="\n")
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                print(f"   ✅ [Local] 本地抓取成功，长度: {len(text)}")
                return text[:12000]
        except Exception as e:
            print(f"   ❌ [Fatal] 所有读取手段均失败: {e}")
        return None

    def _extract_images_from_html(self, html_text, base_url=""):
        """从 HTML 中提取 img 标签的图片 URL，过滤二维码上下文"""
        try:
            qr_context_keywords = [
                '二维码', '扫码', '扫一扫', '关注', '长按识别', '公众号',
                'qrcode', 'qr code', 'scan', 'follow us', 'subscribe',
                '小程序', '微信号', '添加好友', '客服', '群聊',
            ]
            img_tags = re.finditer(r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>', html_text, re.IGNORECASE)
            for match in img_tags:
                u = match.group(1)
                start = max(0, match.start() - 200)
                end = min(len(html_text), match.end() + 200)
                context = html_text[start:end].lower()

                if any(kw in context for kw in qr_context_keywords):
                    continue

                if u.startswith("//"):
                    u = "https:" + u
                elif u.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(base_url)
                    u = f"{parsed.scheme}://{parsed.netloc}{u}"
                if u.startswith("http") and self._is_valid_image_url(u):
                    self._original_images.append(u)
            if self._original_images:
                print(f"   📷 从原文提取到 {len(self._original_images)} 张图片")
        except Exception as e:
            print(f"   ⚠️ 提取原文图片失败: {e}")

    def _extract_images_from_url(self, url):
        """单独请求原文 HTML 来提取图片（用于 Jina 读取成功但没有图片的情况）"""
        try:
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                self._extract_images_from_html(resp.text, url)
        except:
            pass

    @staticmethod
    def _is_valid_image_url(url):
        """过滤掉 logo、icon、二维码、头像等无意义图片"""
        skip_keywords = [
            'logo', 'icon', 'avatar', 'favicon', 'emoji', 'badge',
            'loading', 'placeholder', 'sprite', 'arrow', 'btn',
            'ad_', 'ads_', 'tracker', '1x1', 'pixel', 'blank',
            'qrcode', 'qr_code', 'qr-code', 'barcode', 'wechat_qr',
            'miniprogram', 'mini_program', 'wxcode', 'weixin',
            'erweima', 'ewm', 'share_img', 'reward', 'donate',
            'follow', 'subscribe', 'gzh', 'gongzhonghao',
        ]
        url_lower = url.lower()
        if any(kw in url_lower for kw in skip_keywords):
            return False
        skip_extensions = ['.svg', '.gif', '.ico', '.webp']
        if any(url_lower.endswith(ext) for ext in skip_extensions):
            return False
        return True

    def _fetch_via_ssh(self, url):
        print(f"   🔄 [SSH] 正在通过远程服务器 {SSH_CONFIG['host']} 抓取...")
        ssh = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=SSH_CONFIG["host"], port=SSH_CONFIG["port"],
                username=SSH_CONFIG["username"], password=SSH_CONFIG["password"],
                timeout=10,
            )
            cmd = f'curl -sL --max-time 20 -H "User-Agent: Mozilla/5.0" "{url}"'
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
            output = stdout.read().decode("utf-8", errors="ignore")
            if len(output) > 100:
                print(f"   ✅ [SSH] 远程抓取成功，长度: {len(output)}")
                return output[:12000]
            else:
                print("   ⚠️ [SSH] 远程抓取内容过短，跳过")
        except Exception as e:
            print(f"   ⚠️ [SSH] 远程抓取失败: {e}")
        finally:
            if ssh:
                ssh.close()
        return None

    # ==================== 搜索图片 ====================
    def _collect_candidate_images(self, title, count=5):
        """收集候选图片：原文图片优先，不够再搜索补充"""
        candidates = []
        seen = set()

        # 来源 1：原文提取的图片（最相关）
        for u in getattr(self, '_original_images', []):
            if u not in seen:
                candidates.append(u)
                seen.add(u)

        if candidates:
            print(f"   📷 原文图片候选: {len(candidates)} 张")

        # 来源 2：DuckDuckGo 搜索（用短关键词，提高命中率）
        if len(candidates) < count:
            short_kw = re.sub(r'[：:，,。.！!？?|｜—–\-"""\'\']', ' ', title)
            short_kw = ' '.join(short_kw.split()[:6])
            search_urls = self._ddg_image_search(short_kw, count)
            for u in search_urls:
                if u not in seen:
                    candidates.append(u)
                    seen.add(u)

        # 来源 3：用更通用的关键词再搜一轮
        if len(candidates) < count:
            generic_kw = "AI 人工智能 科技"
            search_urls = self._ddg_image_search(generic_kw, count)
            for u in search_urls:
                if u not in seen:
                    candidates.append(u)
                    seen.add(u)

        print(f"   🖼️ 共收集 {len(candidates)} 张候选图片")
        return candidates

    def _ddg_image_search(self, keyword, count=5):
        """DuckDuckGo 图片搜索，本地失败走远程"""
        image_urls = []
        try:
            with DDGS() as ddgs:
                results = list(ddgs.images(keyword, max_results=count))
                for r in results:
                    img_url = r.get("image", "")
                    if img_url and img_url.startswith("http"):
                        image_urls.append(img_url)
        except Exception as e:
            print(f"   ⚠️ [DDG] 本地搜图失败: {e}，尝试远程...")

        if not image_urls:
            image_urls = self._search_images_via_ssh(keyword, count)
        return image_urls

    def _search_images_via_ssh(self, keyword, count=5):
        ssh = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                hostname=SSH_CONFIG["host"], port=SSH_CONFIG["port"],
                username=SSH_CONFIG["username"], password=SSH_CONFIG["password"],
                timeout=10,
            )
            safe_kw = keyword.replace("'", "").replace('"', '')[:50]
            script = (
                'python3 -c "'
                "from duckduckgo_search import DDGS;"
                "import json;"
                f"results = list(DDGS().images('{safe_kw}', max_results={count}));"
                "urls = [r['image'] for r in results if r.get('image','').startswith('http')];"
                "print(json.dumps(urls))"
                '"'
            )
            stdin, stdout, stderr = ssh.exec_command(script, timeout=30)
            output = stdout.read().decode("utf-8", errors="ignore").strip()
            if output:
                return json.loads(output)
        except Exception as e:
            print(f"   ⚠️ [SSH] 远程搜图失败: {e}")
        finally:
            if ssh:
                ssh.close()
        return []

    # ==================== 下载图片 ====================
    def _download_image(self, image_url):
        """下载图片并验证质量，返回 (临时文件路径, content_type) 或 (None, None)"""
        headers_variants = [
            {**self.headers, "Referer": image_url},
            self.headers,
            {"User-Agent": "Mozilla/5.0"},
        ]
        for hdrs in headers_variants:
            try:
                resp = requests.get(image_url, headers=hdrs, timeout=15, allow_redirects=True)
                ct = resp.headers.get("Content-Type", "")
                if resp.status_code != 200:
                    continue
                if "image" not in ct and len(resp.content) < 5000:
                    continue
                if len(resp.content) < 5000:
                    continue

                ext = ".jpg"
                if "png" in ct:
                    ext = ".png"
                elif "gif" in ct:
                    ext = ".gif"
                elif "webp" in ct:
                    ext = ".jpg"

                tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                tmp.write(resp.content)
                tmp.close()

                if not self._check_image_quality(tmp.name):
                    os.unlink(tmp.name)
                    return None, None

                return tmp.name, ct if "image" in ct else "image/jpeg"
            except:
                continue
        return None, None

    @staticmethod
    def _check_image_quality(filepath):
        """检查图片是否为有效的文章配图（严格过滤二维码、空白图、纯色图）"""
        try:
            from PIL import Image
            img = Image.open(filepath)
            w, h = img.size

            if w < 200 or h < 200:
                return False

            sample = img.convert("RGB").resize((100, 100))
            pixels = list(sample.getdata())
            total = len(pixels)

            avg_r = sum(p[0] for p in pixels) / total
            avg_g = sum(p[1] for p in pixels) / total
            avg_b = sum(p[2] for p in pixels) / total

            # ---- 空白/纯色检测 ----
            if avg_r > 245 and avg_g > 245 and avg_b > 245:
                return False
            if avg_r < 10 and avg_g < 10 and avg_b < 10:
                return False
            variance = sum(
                (p[0] - avg_r) ** 2 + (p[1] - avg_g) ** 2 + (p[2] - avg_b) ** 2
                for p in pixels
            ) / total
            if variance < 80:
                return False

            # ---- 二维码检测 ----
            # 二维码特征：大量极黑+极白像素，几乎无彩色，且接近正方形
            dark = sum(1 for p in pixels if p[0] < 50 and p[1] < 50 and p[2] < 50)
            light = sum(1 for p in pixels if p[0] > 200 and p[1] > 200 and p[2] > 200)
            bw_ratio = (dark + light) / total

            # 计算彩色程度：每个像素 RGB 三通道的标准差，越低越灰
            gray_count = 0
            for p in pixels:
                channel_spread = max(p[0], p[1], p[2]) - min(p[0], p[1], p[2])
                if channel_spread < 30:
                    gray_count += 1
            gray_ratio = gray_count / total

            ratio = max(w, h) / min(w, h)

            # 黑白像素占 70%+ 且灰度像素占 85%+ → 二维码
            if bw_ratio > 0.70 and gray_ratio > 0.85:
                return False

            # 接近正方形 + 黑白像素占 60%+ 且灰度占 80%+ → 也是二维码
            if ratio < 1.3 and bw_ratio > 0.60 and gray_ratio > 0.80:
                return False

            # 几乎全灰度（无彩色）且白色占比很高 → 带白底的二维码/条形码
            if gray_ratio > 0.92 and light / total > 0.50:
                return False

            return True
        except:
            return False

    # ==================== 上传图片到微信素材库 ====================
    def _upload_image_to_wechat(self, image_url):
        """下载图片并上传为永久素材，返回 (media_id, wechat_url)"""
        token = self._get_access_token()
        if not token:
            return None, None

        tmp_path, content_type = self._download_image(image_url)
        if not tmp_path:
            print(f"   ⚠️ 图片下载失败: {image_url[:60]}")
            return None, None

        try:
            ext = os.path.splitext(tmp_path)[1]
            upload_url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
            with open(tmp_path, "rb") as f:
                files = {"media": (f"cover{ext}", f, content_type)}
                upload_resp = requests.post(upload_url, files=files).json()

            media_id = upload_resp.get("media_id")
            wechat_url = upload_resp.get("url", "")
            if media_id:
                print(f"   ✅ 封面图上传成功 media_id={media_id[:20]}...")
                return media_id, wechat_url
            else:
                print(f"   ⚠️ 封面图上传失败: {upload_resp}")
                return None, None
        except Exception as e:
            print(f"   ⚠️ 封面图上传异常: {e}")
            return None, None
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass

    def _upload_content_image(self, image_url):
        """下载图片并上传到微信图文正文图片接口，返回微信 URL"""
        token = self._get_access_token()
        if not token:
            return None

        tmp_path, content_type = self._download_image(image_url)
        if not tmp_path:
            return None

        try:
            ext = os.path.splitext(tmp_path)[1]
            upload_url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"
            with open(tmp_path, "rb") as f:
                files = {"media": (f"img{ext}", f, content_type)}
                upload_resp = requests.post(upload_url, files=files).json()
            wx_url = upload_resp.get("url")
            if wx_url:
                print(f"   ✅ 正文图片上传成功")
            return wx_url
        except Exception as e:
            print(f"   ⚠️ 正文图片上传异常: {e}")
            return None
        finally:
            try:
                os.unlink(tmp_path)
            except:
                pass

    # ==================== AI 改写 ====================
    def rewrite_article(self, original_text):
        print(f"✍️ [4/6] 正在使用 {LLM_CONFIG['model_name']} 进行 AI 改写...")

        system_prompt = """你是一位精通人工智能领域的专家，对大模型、深度学习、自然语言处理、计算机视觉等方向有深入研究，同时擅长将前沿技术用通俗易懂的语言讲给大众。

请基于提供的素材，以你的专家视角改写成一篇适合微信公众号发布的原创文章。

要求：
1. **文章字数约 1500 字**，不少于1200 字，不超过 3000 字,中文写作，不要输出其他国家语言。
2. **必须返回 JSON 格式**，包含字段：`title`（标题）、`digest`（80字以内摘要）、`content`（HTML正文）。
3. 写作风格：以专家口吻深入浅出地分析，结构清晰（引入 → 技术解读 → 行业影响 → 展望），开头要有吸引力。
4. 可以加入你作为 AI 专家的独到见解和点评，但不要编造素材中未提及的具体数据。
5. **标题要求**：有吸引力、体现专业深度、风格多样化，最好是有吸引力。
#    - 疑问式："XXX，是泡沫还是未来？"
#    - 数字式："3个关键信号告诉你，XXX正在改变一切"
#    - 观点式："深度解析：为什么XXX将重新定义行业格局"
#    - 故事式："AI重塑程序员职业：中阶工程师最先被洗牌"
#    - 风趣式：Cursor稳如老狗，Trae疯涨更新：程序员到底该选谁？
   请根据素材内容灵活随机选择最合适的标题风格尽量吸引人一点，但是不限于这些风格。

`content` 字段的排版规范（微信公众号内联样式，严格遵守）：

整体用一个 <section> 包裹：
<section style="max-width:680px;margin:0 auto;padding:20px 16px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;color:#333;line-height:1.8;font-size:16px;">

开头导语（第一段，必须有实际内容，用一两句话概括全文核心观点来吸引读者）：
<p style="font-size:15px;color:#666666;border-left:3px solid #1e88e5;padding-left:12px;margin-bottom:24px;background-color:#f8f9fa;padding:12px 16px;">这里写导语的实际内容，不要留空</p>

在导语之后、第一个小标题之前，插入一张配图占位符：
{{IMAGE_1}}

小标题：
<h2 style="font-size:20px;font-weight:700;color:#1a1a1a;margin:28px 0 12px;padding-bottom:8px;border-bottom:2px solid #1e88e5;">标题文字</h2>

正文段落：
<p style="margin:12px 0;text-indent:2em;">段落内容</p>

重点加粗：
<strong style="color:#1e88e5;">重点文字</strong>

引用/专家点评块：
<blockquote style="margin:16px 0;padding:14px 18px;background:#f0f7ff;border-left:4px solid #1e88e5;border-radius:4px;color:#555;font-size:15px;">点评内容</blockquote>

在文章中部（约第二个小标题之后）再插入一张配图占位符：
{{IMAGE_2}}

无序列表：
<ul style="margin:12px 0;padding-left:24px;">
<li style="margin:6px 0;">列表项</li>
</ul>

分隔线（章节之间可选）：
<hr style="border:none;border-top:1px dashed #ddd;margin:24px 0;">

结尾总结段（必须有实际内容，用两三句话总结全文要点和展望，不要留空）：
<section style="margin:20px 0 0;padding:14px 18px;background-color:#1e88e5;color:#ffffff;border-radius:6px;font-size:15px;line-height:1.7;">这里写总结的实际内容，不要留空</section>

最后关闭 </section>。

注意：
- 不要包含 <html>、<head>、<body>。
- 所有样式必须 style 内联写。
- 颜色主题统一蓝色系 #1e88e5。
- 导语和总结段是文章最重要的部分，必须包含有意义的实际文字内容，绝对不能为空或只写"导语内容""总结内容"这样的占位文字。
- 不要输出只有编号没有内容的行（如单独的"1."、"2."、"一、"等）。
- 必须在文中放置 {{IMAGE_1}} 和 {{IMAGE_2}} 两个图片占位符，各占一行，不要加任何其他标签包裹。"""

        try:
            response = self.client.chat.completions.create(
                model=LLM_CONFIG["model_name"],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"素材内容如下：\n\n{original_text}"}
                ],
                response_format={"type": "json_object"}
            )
            content_str = response.choices[0].message.content
            if content_str.startswith("```json"):
                content_str = content_str.replace("```json", "").replace("```", "")
            return json.loads(content_str)
        except Exception as e:
            print(f"❌ 写作/解析失败: {e}")
            return None

    # ==================== 处理图片：收集 → 逐个尝试上传 → 替换占位符 ====================
    def process_images(self, article_json, news_title):
        """收集候选图片 → 逐个尝试上传 → 替换文中占位符 → 返回封面 media_id"""
        print(f"🖼️ [5/6] 正在处理文章配图...")
        content = article_json.get("content", "")
        title = article_json.get("title", news_title)

        candidates = self._collect_candidate_images(title, count=8)

        thumb_media_id = None
        wechat_content_urls = []

        for img_url in candidates:
            if len(wechat_content_urls) >= 2 and thumb_media_id:
                break
            print(f"   🔄 尝试图片: {img_url[:70]}...")

            # 第一张成功的同时作为封面
            if not thumb_media_id:
                mid, wurl = self._upload_image_to_wechat(img_url)
                if mid:
                    thumb_media_id = mid
                    if wurl:
                        wechat_content_urls.append(wurl)
                    else:
                        wx_url = self._upload_content_image(img_url)
                        if wx_url:
                            wechat_content_urls.append(wx_url)
                    continue

            # 后续图片只上传到正文
            if len(wechat_content_urls) < 2:
                wx_url = self._upload_content_image(img_url)
                if wx_url:
                    wechat_content_urls.append(wx_url)

        print(f"   📊 图片结果: 封面={'✅' if thumb_media_id else '❌'}, 正文图片={len(wechat_content_urls)}张")

        img_html_tpl = '<p style="text-align:center;margin:20px 0;"><img src="{url}" style="max-width:100%;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,0.1);" /></p>'

        if wechat_content_urls:
            content = content.replace("{{IMAGE_1}}", img_html_tpl.format(url=wechat_content_urls[0]))
        else:
            content = content.replace("{{IMAGE_1}}", "")

        if len(wechat_content_urls) >= 2:
            content = content.replace("{{IMAGE_2}}", img_html_tpl.format(url=wechat_content_urls[1]))
        else:
            content = content.replace("{{IMAGE_2}}", "")

        content = re.sub(r'\{\{IMAGE_\d+\}\}', '', content)

        article_json["content"] = content
        return thumb_media_id

    # ==================== 清理内容 ====================
    @staticmethod
    def _clean_content(html_content):
        """彻底清理 HTML：去掉所有换行和标签间空白，输出紧凑 HTML 防止微信插入圆点"""
        # 第一步：按行过滤掉只有序号/符号的垃圾行
        junk = re.compile(
            r'^\s*('
            r'[\d]+[.、．:：)\）]?'
            r'|[一二三四五六七八九十百]+[.、．:：)\）]?'
            r'|[\u2460-\u2473\u2776-\u277F\u2474-\u2487\u2488-\u249B'
            r'\u3220-\u3229\u2160-\u216B\u24B6-\u24E9'
            r'\u25CF\u25CB\u25C6\u25C7\u25A0\u25A1\u25AA\u25AB'
            r'\u2605\u2606\u25B6\u25BA\u25B7\u25B8\u25C9\u2299\u229A\u29BF]'
            r')\s*$'
        )
        lines = html_content.splitlines()
        kept = []
        for line in lines:
            s = line.strip()
            if not s:
                continue
            if junk.match(s):
                continue
            kept.append(s)

        # 第二步：拼成一行，压缩标签间所有空白
        result = ''.join(kept)
        result = re.sub(r'>\s+<', '><', result)
        result = re.sub(r'\s{2,}', ' ', result)
        return result

    # ==================== 微信 Token ====================
    def _get_access_token(self):
        if self.wechat_token and time.time() < self.token_expire_time:
            return self.wechat_token
        url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={WECHAT_CONFIG['app_id']}&secret={WECHAT_CONFIG['app_secret']}"
        try:
            resp = requests.get(url).json()
            if "access_token" in resp:
                self.wechat_token = resp["access_token"]
                self.token_expire_time = time.time() + 7000
                return self.wechat_token
            else:
                print(f"❌ 获取 Token 错误: {resp}")
        except Exception as e:
            print(f"❌ 网络请求错误: {e}")
        return None

    # ==================== 发布草稿 ====================
    def publish_draft(self, article_data, thumb_media_id=None):
        print("🚀 [6/6] 正在上传至微信后台...")
        token = self._get_access_token()
        if not token:
            return None

        content = self._clean_content(article_data.get('content', '<p>正文生成失败</p>'))

        article_payload = {
            "title": article_data.get('title', 'AI 每日资讯'),
            "author": AUTHOR,
            "digest": article_data.get('digest', '点击查看详情'),
            "content": content,
            "need_open_comment": 1,
            "only_fans_can_comment": 0,
        }

        # 封面图优先级：搜到的图片 > 素材库已有图片
        if thumb_media_id:
            article_payload["thumb_media_id"] = thumb_media_id
            print(f"   ✅ 使用搜索到的图片作为封面")
        else:
            print("   ⚠️ 无搜索封面图，尝试从素材库获取...")
            try:
                list_url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={token}"
                list_resp = requests.post(list_url, json={"type": "image", "offset": 0, "count": 1}).json()
                if "item" in list_resp and len(list_resp["item"]) > 0:
                    fallback_id = list_resp["item"][0]["media_id"]
                    print(f"   🔄 使用素材库第一张图作为封面: {fallback_id}")
                    article_payload["thumb_media_id"] = fallback_id
                else:
                    print("   ❌ 素材库为空，无法发布（微信强制要求封面）。请先去后台上传一张图片！")
                    return None
            except Exception as e:
                print(f"   ❌ 获取素材列表失败: {e}")
                return None

        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
        payload = {"articles": [article_payload]}

        try:
            resp = requests.post(
                url,
                data=json.dumps(payload, ensure_ascii=False).encode('utf-8')
            ).json()
            if "media_id" in resp:
                print(f"✅ 成功！文章已存入草稿箱。Media ID: {resp['media_id']}")
                print("👉 请前往微信公众号后台 -> 草稿箱 查看并发布。")
                return resp['media_id']
            else:
                print(f"❌ 发布失败，微信返回: {resp}")
        except Exception as e:
            print(f"❌ 发布请求出错: {e}")
        return None

    # ==================== 主流程 ====================
    def run(self):
        news_list = self.search_news()
        if not news_list:
            print("未找到相关新闻，任务结束。")
            return

        total = len(news_list)
        success_count = 0
        fail_count = 0

        for idx, news in enumerate(news_list, 1):
            print(f"\n{'='*50}")
            print(f"📰 [{idx}/{total}] 处理素材: {news['title']}")
            print(f"{'='*50}")

            content = self.fetch_content(news['href'])
            if not content:
                print("⚠️ 内容读取失败，跳过这篇...")
                fail_count += 1
                continue

            article_json = self.rewrite_article(content)
            if not article_json:
                print("⚠️ 改写失败，跳过这篇...")
                fail_count += 1
                continue
            print(f"📝 生成标题: {article_json.get('title')}")

            thumb_media_id = self.process_images(article_json, news['title'])

            res = self.publish_draft(article_json, thumb_media_id)
            if res:
                success_count += 1
                print(f"🎉 第 {idx} 篇发布成功！")
            else:
                fail_count += 1
                print(f"⚠️ 第 {idx} 篇发布失败。")

        print(f"\n{'='*50}")
        print(f"📊 全部完成！成功 {success_count} 篇，失败 {fail_count} 篇，共 {total} 篇")
        print(f"{'='*50}")


if __name__ == "__main__":
    agent = WeChatAIAgent()
    agent.run()
