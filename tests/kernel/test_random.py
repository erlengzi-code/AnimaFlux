"""P2 Kernel 随机服务测试（Gate：RandomService 可复现，§22）。"""

from animaflux.kernel.random import RandomService


def test_same_seed_same_stream_is_reproducible():
    a = RandomService(root_seed=42)
    b = RandomService(root_seed=42)
    seq_a = [a.stream("agent-001", "emotion").random() for _ in range(10)]
    seq_b = [b.stream("agent-001", "emotion").random() for _ in range(10)]
    assert seq_a == seq_b


def test_different_seed_gives_different_stream():
    a = RandomService(root_seed=1).stream("agent-001", "emotion")
    b = RandomService(root_seed=2).stream("agent-001", "emotion")
    assert [a.random() for _ in range(5)] != [b.random() for _ in range(5)]


def test_different_domains_are_isolated():
    s = RandomService(root_seed=42)
    emotion_first = [s.stream("agent-001", "emotion").random() for _ in range(3)]

    # 另一条 service 消费 disease 流，不应影响 emotion 流的序列（§22.4 隔离）
    s2 = RandomService(root_seed=42)
    emotion2 = s2.stream("agent-001", "emotion")
    _ = s2.stream("agent-001", "body.disease").randint(0, 100)
    assert [emotion2.random() for _ in range(3)] == emotion_first


def test_stream_is_reused_not_recreated():
    s = RandomService(root_seed=42)
    assert s.stream("x") is s.stream("x")
