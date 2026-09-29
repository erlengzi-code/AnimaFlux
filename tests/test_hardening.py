"""P12 Hardening 测试（§16D.22 / §16D.23 / §16D.31 / §16D.33 / §16D.34）。"""

from datetime import datetime

from animaflux.api import AnimaFlux
from animaflux.contracts.state import StateNamespace, StateResolutionResult
from animaflux.persistence.inmemory import InMemoryBackend
from animaflux.runtime.lifeloop import LifeRuntime


# ---------------------------------------------------------------------------
# §16D.22 Plugin Replacement（Anti-Coupling）
# ---------------------------------------------------------------------------
def test_plugin_replacement_anti_coupling():
    """故意用不同内部 Schema 的 Owner，框架（resolve/commit/replay）仍应运行。"""

    class DictPersonality:
        """内部 Schema 与 default_life 完全不同：dict 而非 tuple[Trait]。"""

        def __init__(self) -> None:
            self.traits = {"openness": 0.5}

    class DictPersonalityOwner:
        def resolve(self, current_state, influences, context):
            return StateResolutionResult(next_state=current_state, changed=False)

    runtime = LifeRuntime("anti-coupling", InMemoryBackend(), start_time=datetime(2000, 1, 1))
    runtime.register_owner(
        StateNamespace.PERSONALITY, DictPersonalityOwner(),
        serialize=lambda s: dict(s.traits),
    )
    runtime.seed(StateNamespace.PERSONALITY, DictPersonality())
    runtime.step(1.0)

    # 框架不依赖 Default Plugin 私有字段，只依赖 serialize 回调 + Owner.resolve
    assert runtime.backend.read_current("anti-coupling", "personality") == "anti-coupling:personality_v1"
    assert runtime.backend.read_version("anti-coupling:personality_v1").payload == {"openness": 0.5}


# ---------------------------------------------------------------------------
# §16D.23 Environment / LLM Provider Replacement
# ---------------------------------------------------------------------------
def test_llm_provider_replacement():
    from animaflux.llm.call_strategy import LLMCallRequest, LLMCallStrategy

    class ProviderA:
        name = "provider-a"

        def generate(self, inp):
            return {"origin": "A"}

    class ProviderB:
        name = "provider-b"

        def generate(self, inp):
            return {"origin": "B"}

    request = LLMCallRequest(
        logical_call_id="L1", process_id="decision",
        prompt_template_id="t", prompt_version="v", input={},
    )
    assert LLMCallStrategy(ProviderA()).call(request).provider == "provider-a"
    assert LLMCallStrategy(ProviderB()).call(request).provider == "provider-b"


def test_environment_adapter_replacement():
    from animaflux.contracts.environment import ActionIntent, ActionResult
    from animaflux.environment.action_journal import ExternalActionJournal

    class EnvA:
        def submit_action(self, intent: ActionIntent) -> ActionResult:
            return ActionResult(result_id="A", intent_id=intent.intent_id, status="success",
                                world_time=datetime(2000, 1, 1))

    class EnvB:
        def submit_action(self, intent: ActionIntent) -> ActionResult:
            return ActionResult(result_id="B", intent_id=intent.intent_id, status="success",
                                world_time=datetime(2000, 1, 1))

    intent = ActionIntent(intent_id="I1", actor="a", action_type="send", world_time=datetime(2000, 1, 1))
    assert ExternalActionJournal(EnvA()).submit(intent).result_id == "A"
    assert ExternalActionJournal(EnvB()).submit(intent).result_id == "B"


def test_runtime_runs_without_llm_provider():
    """NoLLMProvider：Runtime 启动 / Tick commit / 状态演化 / Checkpoint / Replay 全成立（§16D.31）。"""
    from animaflux.runtime.replay import ReplayEngine

    flux = AnimaFlux()
    handle = flux.create_life("no-llm")
    result = handle.send_text("I sense danger ahead.")
    assert result.committed
    assert handle.inspect(StateNamespace.EMOTION).data.episodes  # 情绪落地，无任何 LLM 调用

    checkpoint = handle.checkpoint()
    assert checkpoint.agent_id == "no-llm"

    engine = ReplayEngine(flux.backend)
    ticks = engine.replay_timeline("no-llm")
    assert engine.llm_calls == 0
    assert len(ticks) > 0


# ---------------------------------------------------------------------------
# §16D.33 Property / Fuzz
# ---------------------------------------------------------------------------
def test_fuzz_emotion_owner_bounded():
    """随机合法 Influence，Emotion 状态不变量（intensity/valence/arousal/mood）恒成立。"""
    from random import Random

    from animaflux.contracts.influence import Influence
    from animaflux.plugins.default_life.emotion import EmotionOwner, EmotionState

    rng = Random(42)
    owner = EmotionOwner()
    state = EmotionState()
    for i in range(200):
        inf = Influence(
            influence_id=f"F{i}", source_plugin="fuzz", target_state="emotion",
            influence_type="emotion.trigger", magnitude=rng.random(),
            created_at=datetime(2000, 1, 1),
            metadata={
                "emotion_type": rng.choice(("joy", "fear", "sadness", "anticipation")),
                "valence": rng.uniform(-1.0, 1.0),
                "arousal": rng.random(),
                "intensity": rng.random(),
            },
        )
        state = owner.resolve(state, (inf,), None).next_state
        for e in state.episodes:
            assert 0.0 <= e.intensity <= 1.0
            assert -1.0 <= e.valence <= 1.0
            assert 0.0 <= e.arousal <= 1.0
        assert -1.0 <= state.mood.valence <= 1.0
        assert 0.0 <= state.mood.arousal <= 1.0


# ---------------------------------------------------------------------------
# §16D.34 Performance / Long-run
# ---------------------------------------------------------------------------
def test_long_run_1000_ticks_stable():
    flux = AnimaFlux()
    handle = flux.create_life("long-run")
    for _ in range(1000):
        handle.step(60.0)

    # 状态仍有效
    emotion = handle.inspect(StateNamespace.EMOTION).data
    for e in emotion.episodes:
        assert 0.0 <= e.intensity <= 1.0
        assert -1.0 <= e.valence <= 1.0

    # Commit Journal：12 个 seed commit + 1000 个 tick commit
    commits = flux.backend.list_commits("long-run")
    assert len(commits) == 12 + 1000


def test_many_memories_experience_rebuild():
    from animaflux.memory.experience import ExperienceIndex
    from animaflux.memory.memory_store import MemoryStore

    store = MemoryStore("many")
    for i in range(1000):
        store.form("episodic", f"event {i}", domain="work.research", importance=0.5)
    index = ExperienceIndex()
    index.rebuild(store.iter_current_memories())
    profile = index.profile()
    assert profile.domain("work.research").exposure == 1000
