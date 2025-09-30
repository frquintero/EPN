# MCP FIRECRAWL Test Output

**Server:** firecrawl
**URL:** https://mcp.firecrawl.dev/fc-1fdc09b3ab964e56a51e1998f8a30a28/v2/mcp
**Input:** Scrape the content from https://api-docs.deepseek.com/ and return it in markdown format focusing only on the main content and code
**Timestamp:** 2025-09-29T14:32:28.644078

---

## Your First API Call  

The DeepSeek API uses an API format compatible with OpenAI. By modifying the configuration, you can use the OpenAI SDK or any software compatible with the OpenAI API to access the DeepSeek API.

| **PARAM** | **VALUE** |
|-----------|-----------|
| `base_url`* | `https://api.deepseek.com` |
| `api_key` | Apply for an [API key](https://platform.deepseek.com/api_keys) |

\* To be compatible with OpenAI, you can also use `https://api.deepseek.com/v1` as the `base_url`. Note that the `v1` here has **no relationship** with the model’s version.  

**Important notes**  

- `deepseek-chat` and `deepseek-reasoner` are now **DeepSeek‑V3.2‑Exp**.  
  - `deepseek-chat` → **non‑thinking mode** of DeepSeek‑V3.2‑Exp  
  - `deepseek-reasoner` → **thinking mode** of DeepSeek‑V3.2‑Exp  

- API access for **V3.1‑Terminus** is still available via an additional interface for comparative testing. See the [comparison testing docs](https://api-docs.deepseek.com/guides/comparison_testing) for details.

---

### Invoke The Chat API  

Once you have an API key, you can call the DeepSeek Chat endpoint. Below is a non‑streaming example (set `"stream": true` for streaming responses).

#### cURL  

```bash
curl https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${DEEPSEEK_API_KEY}" \
  -d '{
        "model": "deepseek-chat",
        "messages": [
          {"role": "system", "content": "You are a helpful assistant."},
          {"role": "user",   "content": "Hello!"}
        ],
        "stream": false
      }'
```

#### Python (using `requests`)  

```python
import requests
import json

url = "https://api.deepseek.com/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {YOUR_DEEPSEEK_API_KEY}"
}
payload = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user",   "content": "Hello!"}
    ],
    "stream": False
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.json())
```

#### Node.js (using `axios`)  

```javascript
const axios = require('axios');

const url = 'https://api.deepseek.com/chat/completions';
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${process.env.DEEPSEEK_API_KEY}`
};

const data = {
  model: 'deepseek-chat',
  messages: [
    { role: 'system', content: 'You are a helpful assistant.' },
    { role: 'user',   content: 'Hello!' }
  ],
  stream: false
};

axios.post(url, data, { headers })
  .then(res => console.log(res.data))
  .catch(err => console.error(err));
```

---  

**Quick reference**

- **Base URL:** `https://api.deepseek.com` (or `https://api.deepseek.com/v1` for OpenAI‑compatible SDKs)  
- **Auth:** `Authorization: Bearer <YOUR_API_KEY>`  
- **Model names:** `deepseek-chat` (non‑thinking), `deepseek-reasoner` (thinking) – both are DeepSeek‑V3.2‑Exp.  

Feel free to adapt the examples to your preferred language or SDK. Happy coding!