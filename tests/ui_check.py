"""Exercise the simplified UI end-to-end via Streamlit AppTest."""
import sys, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
APP = os.path.join(ROOT, "streamlit_app.py")

from streamlit.testing.v1 import AppTest

# --- Ask: computation ---
at = AppTest.from_file(APP, default_timeout=180)
at.run()
at.text_area[0].set_value("compute eigenvalues of [[2,0],[0,3]]")
at.button[0].click().run()
assert not at.exception, at.exception
md = " ".join(m.value for m in at.markdown)
assert "2" in md and "3" in md, "eigenvalues missing from answer"
print("Ask + compute works")

# --- Ask: pasted proof (auto-review) ---
at2 = AppTest.from_file(APP, default_timeout=180)
at2.run()
at2.text_area[0].set_value("theorem my_two : 2 + 2 = 4 := by rfl")
at2.button[0].click().run()
assert not at2.exception, at2.exception
md2 = " ".join(m.value for m in at2.markdown)
assert "truth weight" in md2.lower() or "reviewed" in md2.lower(), "review missing"
print("Ask + pasted-proof auto-review works")

# --- Check a proof: all four examples ---
cases = [
    "A correct proof",
    "A proof with a gap (`sorry`)",
    "The wrong setting (Nat lemma on vectors)",
    "Distributivity done properly",
]
for case in cases:
    at3 = AppTest.from_file(APP, default_timeout=180)
    at3.run()
    at3.radio[0].set_value("Check a proof").run()
    assert not at3.exception, at3.exception
    sels = [s for s in at3.selectbox if case in str(s.options)]
    assert sels, f"selectbox with {case!r} not found"
    sels[0].select(case).run()
    at3.button[0].click().run()
    assert not at3.exception, f"{case}: {at3.exception}"
    metrics = [m.value for m in at3.metric]
    assert metrics, f"{case}: no truth-weight metric rendered"
    print(f"  {case[:44]:44s} -> {metrics}")

# --- Advanced drawer renders ---
at4 = AppTest.from_file(APP, default_timeout=180)
at4.run()
# sidebar radios: task radio + advanced radio (inside expander)
radios = list(at4.radio)
assert len(radios) >= 2, "advanced radio not found"
radios[1].set_value("SU(2) analysis").run()
assert not at4.exception, at4.exception
print("Advanced SU(2) page renders")
print("ALL UI WORKFLOWS PASS")
