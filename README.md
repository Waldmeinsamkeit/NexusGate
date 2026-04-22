# NexusGate

鍏峰鏈湴璁板繂鑳藉姏鐨?LLM 缃戝叧锛屾彁渚?OpenAI 鍏煎鍏ュ彛锛屽苟鍦ㄨ姹傝浆鍙戝埌涓婃父妯″瀷鍓嶅畬鎴愶細

- 璁板繂妫€绱笌涓婁笅鏂囨敞鍏?
- 璺?provider 璺敱涓庡洖閫€
- 鍔ㄦ€佷笂涓嬫枃鍘嬬缉
- 鍩轰簬璇佹嵁鐨勫够瑙夋姂鍒?
- 鏈湴 API Key 绠＄悊涓庡鎴风閰嶇疆鍚屾

瀹冮€傚悎閮ㄧ讲鍦ㄦ湰鍦版垨鍐呯綉锛屼綔涓?CLI銆丄gent銆佽嚜鍔ㄥ寲鑴氭湰銆両DE 鎻掍欢銆丱penAI 鍏煎瀹㈡埛绔殑缁熶竴鎺ュ叆灞傘€?

---

## 1. 鏍稿績鑳藉姏

### 1.1 OpenAI 鍏煎缃戝叧鍏ュ彛

褰撳墠鏀寔浠ヤ笅鎺ュ彛锛?

- `POST /v1/chat/completions`
- `POST /v1/responses`
- `POST /v1/messages`
- `GET /health`

浣犲彲浠ユ妸 NexusGate 褰撴垚涓€涓湰鍦?LLM API 鑱氬悎鍏ュ彛锛屽澶栨毚闇茬粺涓€ Base URL锛屽啀鐢卞畠鍐冲畾璁板繂娉ㄥ叆銆佽矾鐢便€佸洖閫€鍜屽畨鍏ㄦ帶鍒躲€?

---

### 1.2 鍒嗗眰璁板繂绯荤粺

NexusGate 浼氬洿缁曡姹傛瀯寤?`MemoryPack`锛屽苟灏嗚蹇嗗垎涓虹ǔ瀹氱粨鏋勫悗鍐嶆覆鏌撳埌涓嶅悓 provider锛?

- `L0`锛氬叏灞€鍏冭鍒?/ 绯荤粺绾х害鏉?
- `constraints`锛氱害鏉熴€佽鍒欍€佺储寮曠被淇℃伅
- `procedures`锛氭妧鑳姐€佹楠ゃ€佸彲澶嶇敤鎿嶄綔缁忛獙
- `continuity`锛氫細璇濊繛缁€х嚎绱€佷换鍔′笂涓嬫枃
- `facts`锛氫笌褰撳墠浠诲姟鐩稿叧鐨勪簨瀹炶蹇?

鍦ㄦ敞鍏ユā鍨嬪墠锛岀郴缁熶細鎸?provider 椋庢牸娓叉煋璁板繂锛?

- OpenAI 椋庢牸鏍囩锛?
  - `<memory_index>`
  - `<relevant_skills>`
  - `<session_recall_hints>`
  - `<relevant_memory>`

- Anthropic Messages 椋庢牸鏍囩锛?
  - `<anthropic_memory_index>`
  - `<anthropic_relevant_skills>`
  - `<anthropic_session_recall_hints>`
  - `<anthropic_relevant_memory>`

---

### 1.3 鍔ㄦ€佷笂涓嬫枃鍘嬬缉

NexusGate 涓嶆槸绠€鍗曞湴鈥滄妸鎵€鏈夎蹇嗛兘濉炶繘鍘烩€濓紝鑰屾槸浼氭牴鎹?provider 鐨勪笂涓嬫枃棰勭畻鎵ц瑁佸壀锛?

- 鍏堟瀯寤烘爣鍑嗗寲 render blocks
- 鍐嶆墽琛?provider-aware trim
- 淇濈暀 canonical section 缁撴瀯
- 鐢熸垚 `trim_report`
- 鍦ㄤ笂涓嬫枃婧㈠嚭鏃朵紭鍏堣繘琛?rerender / trim retry锛岃€屼笉鏄洸鐩け璐?

杩欒瀹冩洿閫傚悎闀垮璇濄€侀暱浠诲姟銆佷唬鐞嗗紡宸ヤ綔娴併€?

---

### 1.4 璺?provider 璺敱涓庡洖閫€

NexusGate 鍐呯疆 `ProviderRouter`锛屽彲鏍规嵁閰嶇疆涓庤姹傜壒寰佽繘琛岃矾鐢憋紝骞跺湪澶辫触鏃跺洖閫€銆?

褰撳墠瀹炵幇鍏峰杩欎簺琛屼负锛?

- 鏍规嵁鐩爣妯″瀷鎴栦笂娓搁厤缃喅瀹?provider
- 鏀寔 direct provider 涓?OpenAI-compatible backend 涓ょ妯″紡
- 鏀寔 fallback chain
- 鏀寔鍚?provider 閲嶈瘯
- 鏀寔涓婁笅鏂囨孩鍑哄悗鐨?rerender trim retry
- 鏀寔宸ュ叿妯″紡涓嶅吋瀹规椂闄嶇骇閲嶈瘯
- 璁板綍 provider 鍋ュ悍淇℃伅涓庨儴鍒嗗洖閫€浜嬩欢

---

### 1.5 骞昏鎶戝埗涓?grounding

鍦ㄨ姹傚彂寰€涓婃父鍓嶏紝NexusGate 浼氶檮鍔?grounding 瑙勫垯涓庤瘉鎹潡锛涘湪鍥炵瓟闃舵锛屽彲缁撳悎鏀寔鎬ф鏌ユ姂鍒跺够瑙夈€?

褰撳墠宸插疄鐜扮殑瀹夊叏鐩稿叧鑳藉姏鍖呮嫭锛?

- 鍩轰簬璁板繂浜嬪疄涓庣害鏉熸瀯寤?evidence blocks
- 閫氳繃 citation block 绾︽潫鍥炵瓟寮曠敤渚濇嵁
- 鍩轰簬 claim support 杩涜妫€鏌?
- 杈撳嚭 `unsupported_ratio`
- 瀵?unsupported claims 鎵ц rewrite / degrade 绛栫暐
- 鍦ㄤ弗鏍兼ā寮忔垨楂橀闄╂儏鍐典笅鏇翠繚瀹堝洖绛?
- 閫氳繃绯荤粺鎻愮ず瑕佹眰鈥滄湭鐭ュ氨璇翠笉鐭ラ亾鈥?

杩欒缃戝叧鏇撮€傚悎鐭ヨ瘑鍨嬮棶绛斻€侀」鐩緟鍔┿€佷唬鐞嗘墽琛岀瓑瀹规槗鍑虹幇鈥滅紪閫犵瓟妗堚€濈殑鍦烘櫙銆?

---

## 2. 杩愯妯″紡

NexusGate 鏀寔涓ょ被涓婃父妯″紡銆?

### 妯″紡 A锛氱洿杩?provider

渚嬪鐩磋繛鏌愪釜 provider 鐨勬ā鍨嬶細

- `TARGET_PROVIDER=claude-sonnet-4-5-20250929`
- 鍚屾椂閰嶇疆瀵瑰簲 provider 鎵€闇€ API Key

### 妯″紡 B锛氳浆鍙戝埌 OpenAI 鍏煎鍚庣

渚嬪杞彂鍒拌嚜寤鸿仛鍚堝眰銆佹湰鍦版ā鍨嬫湇鍔°€佺涓夋柟鍏煎鎺ュ彛锛?

- `TARGET_PROVIDER=gpt-5.3-codex`
- `TARGET_BASE_URL=http://localhost:11434/v1`
- `TARGET_API_KEY=sk-anything`

濡傛灉閰嶇疆浜?`TARGET_BASE_URL`锛孨exusGate 浼氫互 OpenAI-compatible 妯″紡璇锋眰涓婃父銆?

---

## 3. 瀹夎

### 3.1 鐜瑕佹眰

- Python 3.10+
- 鍙闂殑涓婃父妯″瀷鏈嶅姟鎴?OpenAI-compatible 鎺ュ彛

### 3.2 瀹夎渚濊禆

```bash
pip install -r requirements.txt
```

---

## 4. 閰嶇疆

椤圭洰鏍圭洰褰曟彁渚涗簡 `.env.example`锛屽彲澶嶅埗涓?`.env` 鍚庝慨鏀广€?

```bash
cp .env.example .env
```

### 4.1 鍩虹閰嶇疆

```env
APP_NAME=NexusGate-Core
APP_ENV=dev
HOST=0.0.0.0
PORT=8000
REQUEST_TIMEOUT_SECONDS=120
```

### 4.2 鏈湴閴存潈

```env
LOCAL_API_KEY=ng-abc123
API_KEY_REQUIRED=false
LOCAL_API_KEY_STORE_PATH=~/.nexusgate/secrets.json
```

鏀寔浠ヤ笅璇锋眰澶翠箣涓€锛?

- `Authorization: Bearer <token>`
- `x-api-key: <token>`
- `api-key: <token>`

---

### 4.3 涓婃父 provider / OpenAI-compatible 閰嶇疆

```env
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx

TARGET_PROVIDER=gpt-5.3-codex
TARGET_BASE_URL=https://your-openai-compatible-endpoint/v1
TARGET_API_KEY=sk-upstream-xxx
UPSTREAM_API_KEY_REQUIRED=true
DEFAULT_MODEL=claude-sonnet-4-5-20250929
```

瀛楁璇存槑锛?

- `TARGET_PROVIDER`锛氶粯璁ょ洰鏍囨ā鍨嬫垨 provider 鍏ュ彛
- `TARGET_BASE_URL`锛氫笂娓?OpenAI-compatible 鎺ュ彛鍦板潃锛涚暀绌哄垯璧?provider direct 妯″紡
- `TARGET_API_KEY`锛氫笂娓告帴鍙ｆ墍闇€瀵嗛挜
- `DEFAULT_MODEL`锛氶粯璁ゆā鍨嬪悕
- `UPSTREAM_API_KEY_REQUIRED`锛氭槸鍚﹀己鍒惰姹備笂娓?key

---

### 4.4 LLMAPI 鍏煎瀛楁锛坙egacy aliases锛?

涓哄吋瀹规棫閰嶇疆锛屽綋鍓嶄粛淇濈暀锛?

```env
LLMAPI_BASE_URL=
LLMAPI_API_KEY=
LLMAPI_MODEL_PREFIX=llmapi/
LLMAPI_PROVIDER_PREFIX=openai/
```

寤鸿鏂伴儴缃蹭紭鍏堜娇鐢細

- `TARGET_BASE_URL`
- `TARGET_API_KEY`
- `TARGET_PROVIDER`

濡傛灉浣犲墠绔噷瑕佸仛鈥淟LMAPI 鐨?API / Base URL 閰嶇疆鈥濓紝寤鸿 UI 灞傝繖鏍峰鐞嗭細

- 涓诲睍绀哄悕锛歚OpenAI-Compatible Upstream`
- 鍏煎瀵煎叆鍚嶏細`LLMAPI (Legacy)`
- 淇濆瓨鏃剁粺涓€鍐欏叆 `TARGET_*`
- 濡傛娴嬪埌鏃у瓧娈靛瓨鍦紝鍒欏湪鐣岄潰涓彁绀衡€滃凡浠?legacy alias 瀵煎叆鈥?

---

### 4.5 璁板繂閰嶇疆

```env
MEMORY_ENABLED=true
MEMORY_STORE_PATH=memory
MEMORY_SOURCE_ROOT=.
MEMORY_COLLECTION_NAME=nexusgate_memory
MEMORY_TOP_K=6
```

瀛楁璇存槑锛?

- `MEMORY_ENABLED`锛氭槸鍚﹀惎鐢ㄨ蹇嗗寮?
- `MEMORY_STORE_PATH`锛氭湰鍦拌蹇嗗瓨鍌ㄨ矾寰?
- `MEMORY_SOURCE_ROOT`锛氭簮浠ｇ爜 / 宸ヤ綔鐩綍鏍硅矾寰?
- `MEMORY_COLLECTION_NAME`锛氳蹇嗛泦鍚堝悕
- `MEMORY_TOP_K`锛氭瘡娆℃绱㈢殑璁板繂鏉℃暟涓婇檺

---

### 4.6 鏈湴瀹㈡埛绔悓姝ラ厤缃?

```env
CLIENT_SYNC_ENABLED=true
CODEX_CONFIG_PATH=C:/Users/Administrator/.codex/config.toml
CLAUDE_SETTINGS_PATH=C:/Users/Administrator/.claude/settings.json
CODEX_LOCAL_BASE_URL=http://127.0.0.1:8000/v1
CLAUDE_LOCAL_BASE_URL=http://127.0.0.1:8000
```

鐢ㄤ簬鎶婃湰鍦板伐鍏疯嚜鍔ㄦ寚鍚?NexusGate銆?

---

## 5. 鍚姩

### 5.1 浣跨敤搴旂敤宸ュ巶鍚姩

```bash
python -m uvicorn back.nexusgate.app:create_app --factory --host 0.0.0.0 --port 8000
```

### 5.2 鍏煎鏃у惎鍔ㄦ柟寮?

浠撳簱涓篃淇濈暀浜嗘棫绀轰緥锛?

```bash
python -m uvicorn back.nexus_gate_core:app --host 0.0.0.0 --port 8000
```

濡傛柊鐗堟湰浠?`nexusgate.app:create_app` 涓哄噯锛屽缓璁紭鍏堥噰鐢ㄥ簲鐢ㄥ伐鍘傛柟寮忓惎鍔ㄣ€?

---

## 6. API 绀轰緥

### 6.1 Chat Completions

```bash
curl http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ng-abc123" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "messages": [
      {"role": "user", "content": "甯垜鎬荤粨褰撳墠椤圭洰鐨勫惎鍔ㄦ柟寮?}
    ]
  }'
```

### 6.2 Responses API

```bash
curl http://127.0.0.1:8000/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ng-abc123" \
  -d '{
    "model": "gpt-5.3-codex",
    "input": "妫€鏌ュ綋鍓嶄粨搴撶殑 README 鏄惁涓庡疄鐜颁竴鑷?
  }'
```

### 6.3 Anthropic-style Messages

```bash
curl http://127.0.0.1:8000/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: ng-abc123" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 512,
    "messages": [
      {"role": "user", "content": "瑙ｉ噴涓€涓嬭繖涓」鐩殑璁板繂鍒嗗眰"}
    ]
  }'
```

---

## 7. 瀹㈡埛绔帴鍏?

### 7.1 OpenAI 鍏煎瀹㈡埛绔?

- **Base URL**: `http://127.0.0.1:8000/v1`
- **Model**: 浣犲笇鏈涜矾鐢卞埌鐨勬ā鍨嬪悕
- **API Key**: 濡傛灉鍚敤浜嗘湰鍦伴壌鏉冿紝鍒欏～鍐?`LOCAL_API_KEY`

### 7.2 Aider

```bash
aider \
  --model claude-sonnet-4-5-20250929 \
  --api-base http://127.0.0.1:8000/v1
```

### 7.3 Codex / Claude 鏈湴閰嶇疆

鍙粨鍚堜互涓嬮厤缃」鑷姩鎺ュ叆锛?

- `CODEX_CONFIG_PATH`
- `CLAUDE_SETTINGS_PATH`
- `CODEX_LOCAL_BASE_URL`
- `CLAUDE_LOCAL_BASE_URL`

---

## 8. 鍋ュ悍妫€鏌?

```bash
curl http://127.0.0.1:8000/health
```

鍏稿瀷杩斿洖淇℃伅鍖呭惈锛?

- `status`
- `upstream`
- `upstream_mode`
- `auth_mode`
- `local_key_source`
- `sync_status`
- `synced_clients`
- `sync_errors`

杩欏浜庡墠绔鐞嗗彴寰堟湁鐢紝鍙互鐩存帴鍋氣€滅郴缁熺姸鎬佹€昏鈥濄€?

---

## 9. 褰撳墠瀹炵幇閲嶇偣

鍩轰簬褰撳墠浠ｇ爜锛孯EADME 闇€瑕佹槑纭細瀹冨凡缁忎笉鍙槸涓€涓€滆蹇嗘嫾鎺ュ櫒鈥濓紝鑰屾槸涓€涓叿澶囧灞傛帶鍒堕€昏緫鐨勬湰鍦扮綉鍏筹細

- 鏈夊垎灞傝蹇嗕笌 provider-aware render
- 鏈夊姩鎬佽鍓笌 trim report
- 鏈夎矾鐢便€佸洖閫€銆佸悓 provider 閲嶈瘯
- 鏈?grounding 涓庡够瑙夋姂鍒?
- 鏈夋湰鍦?key 涓庡鎴风鍚屾鑳藉姏
- 鏈?OpenAI-compatible 涓?provider-direct 鍙屾ā寮?

---

## 10. 娴嬭瘯

鍙寜浠撳簱鍐呮祴璇曠户缁獙璇佸叧閿兘鍔涳紝渚嬪锛?

```bash
PYTHONPATH=. python -m unittest discover -s tests -p "test_memory_manager.py"
```

寤鸿鍚庣画琛ュ厖鐨勬祴璇曟柟鍚戯細

- 璺敱鍐崇瓥娴嬭瘯
- fallback trace 娴嬭瘯
- grounding rewrite 娴嬭瘯
- OpenAI-compatible upstream 娴嬭瘯
- 绠＄悊鍙?API 娴嬭瘯

---

## 11. 閫傜敤鍦烘櫙

- 鏈湴 coding agent 缃戝叧
- 甯﹁蹇嗙殑 CLI / IDE 鍔╂墜
- 澶氭ā鍨嬬粺涓€鎺ュ叆灞?
- 浼佷笟鍐呴儴鐭ヨ瘑澧炲己闂瓟鍏ュ彛
- 鏈夊璁′笌瀹夊叏瑕佹眰鐨勪唬鐞嗘墽琛岀幆澧?

---

## 12. License

鏈」鐩寘鍚?`LICENSE` 鏂囦欢锛岃鎸変粨搴撲腑鐨勫疄闄呰鍙瘉浣跨敤銆
