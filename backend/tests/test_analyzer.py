import pytest

from app.analyzer import analyze, reset_history


@pytest.fixture(autouse=True)
def clear_analyzer_history():
    reset_history()
    yield
    reset_history()


def test_analyze_returns_risk_fields():
    result = analyze("hello world. this is a stable mock response")
    assert "risk_score" in result
    assert result["risk_label"] in {"LOW", "MEDIUM", "HIGH"}
    assert "model_probabilities" in result
    assert result["context_key"] == "global"
    assert result["baseline_status"] == "cold_start"
    assert "signals" in result


def test_deepseek_official_api_responses_do_not_become_risky_while_baseline_is_warming():
    responses = [
        "我是 DeepSeek 官方 API 返回的正常回答。请问有什么可以帮助你？",
        "这个请求已经完成。下面是简短结论：DeepSeek API 可正常使用。",
        "你好！我是 DeepSeek，很高兴为你服务。",
    ]
    context = {"provider": "deepseek", "model": "deepseek-chat"}

    results = [analyze(responses[index % len(responses)], context=context) for index in range(10)]

    assert all(result["risk_label"] == "LOW" for result in results)
    assert all(not result["mixed_model"] for result in results)
    assert results[-1]["context_key"] == "deepseek:deepseek-chat"
    assert results[-1]["baseline_status"] == "warming"


def test_gpt55_official_api_responses_do_not_become_risky_while_baseline_is_warming():
    responses = [
        "GPT-5.5 official API response: The request was completed successfully. How can I help you next?",
        "Here is a concise answer: the configuration looks valid and the API is responding normally.",
        "I can help with coding, analysis, writing, or debugging. Please share the task you want to complete.",
        "你好，我是 GPT-5.5 官方 API 返回的正常回答。有什么可以帮你？",
    ]
    context = {"provider": "openai", "model": "gpt-5.5"}

    results = [analyze(responses[index % len(responses)], context=context) for index in range(10)]

    assert all(result["risk_label"] == "LOW" for result in results)
    assert all(not result["mixed_model"] for result in results)
    assert results[-1]["context_key"] == "openai:gpt-5.5"
    assert results[-1]["baseline_status"] == "warming"


def test_context_baselines_are_isolated_between_models():
    deepseek_context = {"provider": "deepseek", "model": "deepseek-chat"}
    gpt_context = {"provider": "openai", "model": "gpt-5.5"}

    for index in range(25):
        analyze(f"DeepSeek 官方 API 正常回答 {index}。这个请求已经完成。", context=deepseek_context)

    result = analyze("GPT-5.5 official API response: The request completed normally.", context=gpt_context)

    assert result["context_key"] == "openai:gpt-5.5"
    assert result["baseline_size"] == 0
    assert result["baseline_status"] == "cold_start"
    assert result["risk_label"] == "LOW"


def test_ready_baseline_can_still_warn_on_hard_failure_pattern():
    context = {"provider": "deepseek", "model": "deepseek-chat"}
    for index in range(25):
        analyze(f"DeepSeek 官方 API 正常回答 {index}。这个请求已经完成。", context=context)

    result = analyze(
        "Traceback (most recent call last):\nException: model failed failed with error: invalid upstream response",
        context=context,
    )

    assert result["baseline_status"] == "ready"
    assert result["risk_score"] >= 0.42
    assert result["risk_label"] in {"MEDIUM", "HIGH"}
    assert result["signals"]["failure_terms"]["hard_failure"] is True


def test_mixed_model_stays_false_until_baseline_is_ready():
    context = {"provider": "openai", "model": "gpt-5.5"}
    results = [analyze(f"Normal GPT-5.5 response number {index}.", context=context) for index in range(19)]

    assert all(not result["mixed_model"] for result in results)
    assert results[-1]["baseline_status"] == "warming"
