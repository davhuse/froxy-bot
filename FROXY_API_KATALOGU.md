# Froxy API ve model kataloğu

Froxy gateway artık sohbet ve görsel sağlayıcılarının tamamını tek bir sağlık kataloğunda gösterir. Katalog sağlayıcı anahtarlarını veya değerlerini dışarı vermez; yalnızca sağlayıcı adı, yetenek, yapılandırma durumu ve doğrulanmış model sayılarını döndürür.

## Sohbet sağlayıcıları

| Sağlayıcı | Render değişkeni | Yetenek |
|---|---|---|
| OpenRouter | `OPENROUTER_API_KEYS` | Sohbet |
| Groq | `GROQ_API_KEYS` | Sohbet |
| NVIDIA | `NVIDIA_API_KEY` | Sohbet |
| Together | `TOGETHER_API_KEYS` | Sohbet + görsel |
| Cerebras | `CEREBRAS_API_KEY` | Sohbet |
| SambaNova | `SAMBANOVA_API_KEY` | Sohbet |
| Google Gemini | `GEMINI_API_KEYS` veya `GOOGLE_API_KEY` | Sohbet + görsel |
| OpenAI | `OPENAI_CHAT_KEY` veya `OPENAI_API_KEY` | Sohbet + görsel |
| AI/ML API | `AIMLAPI_KEY` | Sohbet + görsel |
| Hugging Face | `HF_TOKEN` | Sohbet |
| Mistral | `MISTRAL_API_KEY` | Sohbet |
| Fireworks | `FIREWORKS_API_KEY` | Sohbet |
| xAI | `XAI_API_KEY` | Sohbet |
| DeepSeek | `DEEPSEEK_API_KEY` | Sohbet |
| Chutes | `CHUTES_API_KEY` | Sohbet |
| EvoLink | `EVOLINK_API_KEYS` | Sohbet + görsel |
| HCNSEC | `HCNSEC_API_KEYS` | Sohbet |
| FreeModel | `FREEMODEL_API_KEYS` | Sohbet |
| Shenfeng | `SHENFENG_GEMINI_KEY` / `SHENFENG_OPENAI_KEY` | Sohbet |
| GuiCore | `GUICORE_CLAUDE_KEY` / `GUICORE_GEMINI_KEY` | Sohbet |
| Pollinations | `POLLINATIONS_API_KEYS` | Sohbet + görsel |
| WaveSpeedAI | `WAVESPEED_API_KEYS` | Görsel |
| Cloudflare Workers AI | `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_API_TOKEN` | Sohbet + görsel |

## Görsel sağlayıcıları

OpenAI GPT Image/DALL·E, Together FLUX/Qwen/Imagen, Cloudflare SDXL/FLUX, Runware FLUX/SDXL, Pollinations Z-Image/FLUX/GPT Image/Nano Banana, AI/ML API FLUX/Nano Banana, Stability Core/Ultra, Gemini/Imagen, ImageGPT, Modal ve EvoLink görsel modelleri katalogda tanımlıdır. Mini App aktif olanları seçilebilir, anahtarı eksik olanları ise `API anahtarı bekleniyor` olarak gösterir.

Anahtarlar bu dosyaya, `.env` dosyasına veya repoya yazılmamalıdır. Render Environment bölümüne eklenmeli ve sonrasında sağlayıcı sağlık kontrolü ile gerçek bir istek doğrulanmalıdır. Bir sağlayıcı için anahtar yokken sahte model yayınlanmaz; bu, kullanıcı bakiyesinin başarısız isteklerde harcanmasını önler.

Canlı kontrol uçları:

- `GET /froxy/api/health`: sağlayıcı ve görsel envanteri
- `GET /froxy/api/models`: aktif sohbet modelleri + sağlayıcı envanteri
- `GET /froxy/api/image-models`: tüm görsel tanımları ve `active` durumu
- `GET /froxy/api/provider-status`: çalışma zamanı sağlayıcı durumları (Telegram Mini App kimliği gerekir)
