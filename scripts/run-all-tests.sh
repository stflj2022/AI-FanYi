#!/bin/bash
# 分批运行所有测试，避免 aiosqlite 和 torch 之间的冲突

set -e

cd "$(dirname "$0")/.."

echo "==================================="
echo "运行全部测试（分批执行）"
echo "==================================="

total_passed=0
total_failed=0
total_skipped=0

# 第1批：核心模型和数据库测试
echo ""
echo ">>> 第1批：核心模型和数据库测试"
if .venv/bin/python -m pytest src/filmdub/tests/test_models.py src/filmdub/tests/test_artifact_registry.py src/filmdub/tests/test_character_db.py src/filmdub/tests/test_relationships.py -q --tb=no; then
    passed=$(.venv/bin/python -m pytest src/filmdub/tests/test_models.py src/filmdub/tests/test_artifact_registry.py src/filmdub/tests/test_character_db.py src/filmdub/tests/test_relationships.py -q --tb=no 2>&1 | grep "passed" | tail -1)
    echo "✓ 第1批通过: $passed"
    # 提取通过的测试数量
    num_passed=$(echo $passed | grep -oP '\d+(?= passed)')
    total_passed=$((total_passed + num_passed))
else
    echo "✗ 第1批失败"
    exit 1
fi

# 第2批：API 测试
echo ""
echo ">>> 第2批：API 测试"
if .venv/bin/python -m pytest src/filmdub/tests/test_api.py -q --tb=no; then
    passed=$(.venv/bin/python -m pytest src/filmdub/tests/test_api.py -q --tb=no 2>&1 | grep "passed" | tail -1)
    echo "✓ 第2批通过: $passed"
    num_passed=$(echo $passed | grep -oP '\d+(?= passed)')
    total_passed=$((total_passed + num_passed))
else
    echo "✗ 第2批失败"
    exit 1
fi

# 第3批：业务逻辑测试
echo ""
echo ">>> 第3批：业务逻辑测试"
if .venv/bin/python -m pytest src/filmdub/tests/test_speaker_mapping.py src/filmdub/tests/test_voice_synthesis.py src/filmdub/tests/test_dialogue_prosody.py -q --tb=no; then
    passed=$(.venv/bin/python -m pytest src/filmdub/tests/test_speaker_mapping.py src/filmdub/tests/test_voice_synthesis.py src/filmdub/tests/test_dialogue_prosody.py -q --tb=no 2>&1 | grep "passed" | tail -1)
    echo "✓ 第3批通过: $passed"
    num_passed=$(echo $passed | grep -oP '\d+(?= passed)')
    total_passed=$((total_passed + num_passed))
else
    echo "✗ 第3批失败"
    exit 1
fi

# 第4批：音频场景分析测试
echo ""
echo ">>> 第4批：音频场景分析测试"
if .venv/bin/python -m pytest src/filmdub/tests/test_audio_scene_analysis.py -q --tb=no; then
    passed=$(.venv/bin/python -m pytest src/filmdub/tests/test_audio_scene_analysis.py -q --tb=no 2>&1 | grep "passed" | tail -1)
    echo "✓ 第4批通过: $passed"
    num_passed=$(echo $passed | grep -oP '\d+(?= passed)')
    total_passed=$((total_passed + num_passed))
else
    echo "✗ 第4批失败"
    exit 1
fi

# 第5批：Adapter 测试
echo ""
echo ">>> 第5批：Adapter 测试"
if .venv/bin/python -m pytest src/filmdub/tests/adapter/ -q --tb=no; then
    passed=$(.venv/bin/python -m pytest src/filmdub/tests/adapter/ -q --tb=no 2>&1 | grep "passed" | tail -1)
    echo "✓ 第5批通过: $passed"
    num_passed=$(echo $passed | grep -oP '\d+(?= passed)')
    total_passed=$((total_passed + num_passed))
    # 提取跳过的测试数量
    num_skipped=$(echo $passed | grep -oP '\d+(?= skipped)' || echo 0)
    total_skipped=$((total_skipped + num_skipped))
else
    echo "✗ 第5批失败"
    exit 1
fi

# 第6批：Face Tracking 测试
echo ""
echo ">>> 第6批：Face Tracking 测试"
if .venv/bin/python -m pytest src/filmdub/tests/face_tracking/ -q --tb=no; then
    passed=$(.venv/bin/python -m pytest src/filmdub/tests/face_tracking/ -q --tb=no 2>&1 | grep "passed" | tail -1)
    echo "✓ 第6批通过: $passed"
    num_passed=$(echo $passed | grep -oP '\d+(?= passed)')
    total_passed=$((total_passed + num_passed))
else
    echo "✗ 第6批失败"
    exit 1
fi

# 第7批：Worker 集成测试
echo ""
echo ">>> 第7批：Worker 集成测试"
if .venv/bin/python -m pytest src/filmdub/tests/workers_integration/ -q --tb=no; then
    passed=$(.venv/bin/python -m pytest src/filmdub/tests/workers_integration/ -q --tb=no 2>&1 | grep "passed" | tail -1)
    echo "✓ 第7批通过: $passed"
    num_passed=$(echo $passed | grep -oP '\d+(?= passed)')
    total_passed=$((total_passed + num_passed))
    # 提取跳过的测试数量
    num_skipped=$(echo $passed | grep -oP '\d+(?= skipped)' || echo 0)
    total_skipped=$((total_skipped + num_skipped))
else
    echo "✗ 第7批失败"
    exit 1
fi

echo ""
echo "==================================="
echo "全部测试通过！"
echo "==================================="
echo "总计: $total_passed passed, $total_skipped skipped"
echo "==================================="
exit 0
