"""Tests for the rule-based differential refinement engine."""
import asyncio

from app.config import get_settings
from app.llm.orchestrator import Orchestrator
from app.llm.providers import ScriptedProvider
from app.ml import differential
from app.schemas import ClinicalBrief, Mode, Prediction
from app.services.sessions import Session


def test_initial_posterior_normalises_and_reflects_prior():
    top = [Prediction(disease="Psoriasis", confidence=0.9, index=6),
           Prediction(disease="Eczema", confidence=0.07, index=2)]
    post = differential.initial_posterior(top)
    assert abs(sum(post.values()) - 1.0) < 1e-6
    assert differential.leading(post)[0] == "Psoriasis"


def test_answers_can_change_the_leading_diagnosis():
    # the image leans Psoriasis...
    top = [Prediction(disease="Psoriasis", confidence=0.8, index=6),
           Prediction(disease="Atopic Dermatitis", confidence=0.15, index=1)]
    post = differential.initial_posterior(top)
    # ...but the answers point to atopic dermatitis
    post = differential.update(post, "silvery_plaques", "no")
    post = differential.update(post, "nail_changes", "no")
    post = differential.update(post, "childhood_atopy", "yes")
    post = differential.update(post, "flexural_itch", "yes")
    lead, conf = differential.leading(post)
    assert lead == "Atopic Dermatitis"
    assert post["Psoriasis"] < 0.5      # confidence moved away from the image's guess


def test_unsure_leaves_posterior_unchanged():
    post = differential.initial_posterior([Prediction(disease="Psoriasis", confidence=0.8, index=6)])
    assert differential.update(post, "silvery_plaques", "unsure") == post


def test_next_feature_does_not_repeat():
    post = differential.initial_posterior([Prediction(disease="Psoriasis", confidence=0.8, index=6)])
    f1 = differential.next_feature(post, set())
    assert f1 is not None
    f2 = differential.next_feature(post, {f1.id})
    assert f2 is not None and f2.id != f1.id


def test_normalise_answer():
    assert differential.normalise_answer("Yes") == "yes"
    assert differential.normalise_answer("No") == "no"
    assert differential.normalise_answer("nope") == "no"
    assert differential.normalise_answer("two weeks, itchy at night") == "unsure"


def test_orchestrator_runs_differential_and_refines_result():
    brief = ClinicalBrief(
        mode=Mode.NORMAL, disease="Psoriasis", confidence=0.99, entropy=0.1,
        top_k=[Prediction(disease="Psoriasis", confidence=0.8, index=6),
               Prediction(disease="Atopic Dermatitis", confidence=0.15, index=1)],
    )
    orch = Orchestrator(ScriptedProvider(), get_settings())
    sess = Session(id="s1", user_id="u1", brief=brief)

    msg, awaiting = asyncio.run(orch.begin(sess))
    assert awaiting and sess.options == ["Yes", "No", "Not sure"] and sess.pending_feature

    done = False
    for _ in range(get_settings().max_questions + 1):
        turn = asyncio.run(orch.reply(sess, "No"))
        if turn.done:
            done = True
            break
    assert done and sess.result is not None
    # the final confidence is the refined posterior, not the image's 0.99
    assert sess.result.confidence != 0.99
