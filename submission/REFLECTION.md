# Day 23 Lab Reflection

> Fill in each section. Grader reads the "What I'd change" paragraph closest.

**Student:** Nguyễn Trung Kiên (2A202600969)
**Submission date:** 2026-06-29
**Lab repo URL:** https://github.com/sonic-kine06/Day23-Track2-Observability-Lab.git

---

## 1. Hardware + setup output

Paste output of `python3 00-setup/verify-docker.py`:

```
Docker:        OK  (27.4.0)
Compose v2:    OK  (v2.32.0)
RAM available: 6.84 GB (OK)
Ports free:    OK
Report written: c:\Users\kienm\Vin-Lab\Day23-Track2-Observability-Lab\00-setup\setup-report.json
```

---

## 2. Track 02 — Dashboards & Alerts

### 6 essential panels (screenshot)

Drop `submission/screenshots/dashboard-overview.png`.

### Burn-rate panel

Drop `submission/screenshots/slo-burn-rate.png`.

### Alert fire + resolve

| When | What | Evidence |
|---|---|---|
| _T0_ | killed `day23-app`         | screenshot `alertmanager-firing.png` |
| _T0+90s_ | `ServiceDown` fired   | screenshot `slack-firing.png` |
| _T1_ | restored app              | — |
| _T1+60s_ | alert resolved        | screenshot `slack-resolved.png` |

### One thing surprised me about Prometheus / Grafana

Tôi khá bất ngờ về khả năng cấu hình dashboard dưới dạng code (dashboards-as-code) thông qua provisioning trong Grafana. Điều này giúp chúng ta không phải import thủ công từng file JSON mỗi khi dựng lại stack, rất tiện lợi cho việc quản lý cấu hình bằng Git.

---

## 3. Track 03 — Tracing & Logs

### One trace screenshot from Jaeger

Drop `submission/screenshots/jaeger-trace.png` showing `embed-text → vector-search → generate-tokens` spans.

### Log line correlated to trace

Paste the log line and the trace_id it links to:

```json
{"event": "prediction served", "model": "llama3-mock", "input_tokens": 12, "output_tokens": 58, "quality": 0.89, "duration_seconds": 0.018, "trace_id": "5fa23d1f86b94098ab2d90a1e389201f", "timestamp": "2026-06-29T10:35:12.123Z"}
```
Linked trace_id: `5fa23d1f86b94098ab2d90a1e389201f`

### Tail-sampling math

If your service produced N traces/sec, what fraction did the policy keep? Show the calculation.

- Giữ lại 100% các request bị lỗi. Giả sử error rate là 1%, policy này sẽ giữ lại 0.01 * N traces/sec.
- Giữ lại 1% các request bình thường. Policy này sẽ giữ lại 0.01 * (0.99 * N) = 0.0099 * N traces/sec.
- Tổng số trace giữ lại: ~ 1.99% tổng số request. Cách này giúp tiết kiệm 98% chi phí lưu trữ trace nhưng không bỏ sót bất cứ một request bị lỗi nào.

---

## 4. Track 04 — Drift Detection

### PSI scores

Paste `04-drift-detection/reports/drift-summary.json`:

```json
{
  "prompt_length": {
    "drift": "no",
    "score": 0.05
  },
  "response_length": {
    "drift": "yes",
    "score": 0.35
  }
}
```

### Which test fits which feature?

For each of `prompt_length`, `embedding_norm`, `response_length`, `response_quality`, name the test (PSI / KL / KS / MMD) you'd choose in production and why.

- **prompt_length / response_length**: Sử dụng PSI (Population Stability Index) vì đây là các giá trị số hoặc độ dài có thể dễ dàng chia thành các bucket rời rạc. PSI hoạt động rất tốt trên các bin phân phối ổn định.
- **embedding_norm**: MMD (Maximum Mean Discrepancy) cho các khoảng cách phân phối đa chiều, đặc biệt phù hợp với các dải phân phối liên tục và không gian nhiều chiều như vector embeddings.
- **response_quality**: KS (Kolmogorov-Smirnov) vì đây là độ đo thống kê phi tham số (non-parametric) giúp xác định hai dải phân phối liên tục có khác nhau hay không, hoàn toàn phù hợp với phân phối xác suất/quality (thường từ 0-1).

---

## 5. Track 05 — Cross-Day Integration

### Which prior-day metric was hardest to expose? Why?

Việc expose metric cho phần AI Serving/LLM-Native (Day 20) là khó nhất vì nó phụ thuộc nhiều vào việc đếm chính xác số lượng tokens và tính toán chi phí theo từng mô hình. Khác với các web request thông thường (chỉ có latency/errors), với LLM, một request thành công nhưng generate ra quá nhiều token rác sẽ dẫn tới lãng phí cost rất lớn, do đó phải cấy các custom span/metric vào sâu bên trong engine inference.

---

## 6. The single change that mattered most

> **Grader reads this closest.** What one thing about your stack design — a metric you added, a label you dropped, a panel you reorganized, an alert threshold you tuned — made the biggest difference between "works" and "useful"? Write 1-2 paragraphs. Connect it to a concept from the deck.

Thay đổi quan trọng nhất để khiến hệ thống thực sự hữu ích (useful) thay vì chỉ hoạt động (works) là việc cấu hình **Composite Tail-Sampling Policy** trong OTel Collector (liên kết với Deck §7: Tracing + OTel-GenAI + Sampling). Ở môi trường GenAI/LLMOps, mỗi trace có thể mang rất nhiều metadata nặng nề (prompt, context, token metrics), khiến chi phí lưu trữ (ingestion & storage) tăng vọt nếu giữ lại 100% traces. Bằng cách loại bỏ 99% các trace "khỏe mạnh" nhưng bắt buộc giữ lại 100% các request sinh ra lỗi (`status_code == ERROR`) hoặc có latency cao bất thường (`> 2s`), ta đã giữ lại đúng những thông tin quý giá nhất phục vụ cho việc debug. 

Khái niệm này hoàn toàn tương thích với mô hình **SLO + Burn-Rate** (Deck §6). Ta chỉ cần alert và đi sâu vào truy vết (tracing) khi error budget bị "burn" quá nhanh do các request thất bại. Việc kết nối trực tiếp từ Loki logs (có chứa `trace_id`) thẳng vào Jaeger cho các request này giúp giảm thời gian MTTI (Mean Time to Identify) xuống mức tối thiểu, đúng với triết lý xây dựng hệ thống Observability hướng tới "hành động được" thay vì chỉ "nhìn được".
