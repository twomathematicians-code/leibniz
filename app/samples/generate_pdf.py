"""
Generate a branded sample PDF of Linear Algebra proofs for upload testing.
Produces app/samples/linear_algebra_proofs.pdf (3 pages, multi-step proofs).

Each theorem is laid out so pdfplumber can extract the Lean statement (line
containing "theorem") and the proof (line containing "by ").

Run:  python app/samples/generate_pdf.py
"""

from __future__ import annotations
import os
from fpdf import FPDF  # type: ignore

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "linear_algebra_proofs.pdf")

INK = (0, 0, 0)
MUTED = (107, 114, 128)
LINE = (229, 231, 235)


class BrandedPDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, "LEIBNIZ  ·  LINEAR ALGEBRA PROOF SET", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*LINE)
        self.line(15, 16, 195, 16)
        self.ln(2)
        self.set_text_color(*INK)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 10, f"Two Mathematicians  ·  Page {self.page_no()}  ·  Leibniz Sample", align="C")

    def section_label(self, text):
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 5, text.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*INK)

    def theorem_title(self, num, name):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*INK)
        self.cell(0, 8, f"{num}.  {name}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, text):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*INK)
        self.multi_cell(0, 5.2, text)
        self.ln(1.5)

    def informal(self, text):
        self.set_font("Helvetica", "I", 10)
        self.set_text_color(*INK)
        self.multi_cell(0, 5.2, text)
        self.ln(1)

    def lean_block(self, statement, proof):
        """Monospace block — the extractor reads 'theorem' and 'by ' lines."""
        self.set_fill_color(243, 244, 246)
        self.set_draw_color(*LINE)
        x, y, w = 15, self.get_y(), 180
        # statement
        self.set_xy(x, y)
        self.set_font("Courier", "", 9)
        self.set_text_color(*INK)
        self.multi_cell(w, 5.2, statement, border=1, fill=True)
        # proof on its own line (starts with spaces + "by ")
        self.set_x(x)
        self.multi_cell(w, 5.2, "  " + proof, border=1, fill=True)
        self.ln(3)


def build():
    pdf = BrandedPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # ── PAGE 1 ──────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*INK)
    pdf.cell(0, 12, "Linear Algebra", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 12)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 7, "A proof set for the Leibniz proof-verifier", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_draw_color(*INK)
    pdf.line(15, 38, 195, 38)
    pdf.ln(4)

    pdf.body(
        "This document presents five theorems from undergraduate linear algebra, "
        "each accompanied by an informal argument and a formal Lean 4 proof. "
        "Upload this PDF to the Leibniz engine to verify every theorem against "
        "the three gates: Validity, Alignment, and Reading."
    )
    pdf.body(
        "Throughout, we model vectors as functions Fin n -> R (pointwise operations). "
        "This reduces vector-space axioms to the corresponding field axioms of the "
        "real numbers, applied componentwise via the ext tactic."
    )
    pdf.ln(2)

    pdf.section_label("Theorem 1")
    pdf.theorem_title("1", "Commutativity of vector addition")
    pdf.informal("Statement:  For all vectors v, w in R^n,  v + w = w + v.")
    pdf.body(
        "Informal argument.  Vector addition is defined pointwise: (v + w)(i) = v(i) + w(i). "
        "Since addition of real numbers is commutative, v(i) + w(i) = w(i) + v(i) for every "
        "component i. The extensionality tactic ext i reduces the goal to equality at each "
        "component, where add_comm closes it."
    )
    pdf.section_label("Formal Lean 4 proof")
    pdf.lean_block(
        "theorem add_comm_vec (v w : Fin n -> R) : v + w = w + v",
        "by ext i; exact add_comm (v i) (w i)"
    )

    pdf.section_label("Theorem 2")
    pdf.theorem_title("2", "Associativity of vector addition")
    pdf.informal("Statement:  For all u, v, w in R^n,  (u + v) + w = u + (v + w).")
    pdf.body(
        "Informal argument.  Again pointwise: ((u + v) + w)(i) = (u(i) + v(i)) + w(i), which "
        "equals u(i) + (v(i) + w(i)) by associativity of real addition. The same ext i / "
        "add_assoc pattern discharges the goal."
    )
    pdf.section_label("Formal Lean 4 proof")
    pdf.lean_block(
        "theorem add_assoc_vec (u v w : Fin n -> R) : (u + v) + w = u + (v + w)",
        "by ext i; exact add_assoc (u i) (v i) (w i)"
    )

    # ── PAGE 2 ──────────────────────────────────────────────
    pdf.add_page()

    pdf.section_label("Theorem 3")
    pdf.theorem_title("3", "Distributivity of scalar multiplication over addition")
    pdf.informal("Statement:  For all c in R and v, w in R^n,  c * (v + w) = c * v + c * w.")
    pdf.body(
        "Informal argument.  Scalar multiplication acts pointwise: (c * (v + w))(i) = "
        "c * (v(i) + w(i)). By distributivity of multiplication over addition in R, this "
        "equals c * v(i) + c * w(i) = (c * v + c * w)(i). The tactic mul_add supplies the "
        "field law at each component after ext i opens the extensionality goal."
    )
    pdf.body(
        "Remark.  This is the first non-trivial vector-space axiom: it couples the additive "
        "and multiplicative structure of the field. Getting it right componentwise is the "
        "core check that R^n is genuinely an R-module, not merely an abelian group."
    )
    pdf.section_label("Formal Lean 4 proof")
    pdf.lean_block(
        "theorem smul_add_vec (c : R) (v w : Fin n -> R) : c * (v + w) = c * v + c * w",
        "by ext i; exact mul_add c (v i) (w i)"
    )

    pdf.section_label("Theorem 4")
    pdf.theorem_title("4", "Left distributivity over scalar addition")
    pdf.informal("Statement:  For all c, d in R and v in R^n,  (c + d) * v = c * v + d * v.")
    pdf.body(
        "Informal argument.  Pointwise: ((c + d) * v)(i) = (c + d) * v(i) = c * v(i) + "
        "d * v(i) by left distributivity in R. The add_mul lemma discharges each component."
    )
    pdf.section_label("Formal Lean 4 proof")
    pdf.lean_block(
        "theorem add_smul_vec (c d : R) (v : Fin n -> R) : (c + d) * v = c * v + d * v",
        "by ext i; exact add_mul c d (v i)"
    )

    # ── PAGE 3 ──────────────────────────────────────────────
    pdf.add_page()

    pdf.section_label("Theorem 5")
    pdf.theorem_title("5", "The identity map has eigenvalue one")
    pdf.informal(
        "Statement:  For every nonzero vector v in R^n, the identity transformation "
        "satisfies id(v) = 1 * v."
    )
    pdf.body(
        "Informal argument.  The identity map leaves every vector unchanged: id(v) = v. "
        "By the unity law of scalar multiplication, 1 * v = v. Hence id(v) = 1 * v, so "
        "every nonzero vector is an eigenvector of the identity with eigenvalue 1. This "
        "is the trivial case of the spectral theorem: the identity is already diagonal."
    )
    pdf.body(
        "Note on the nonzero hypothesis.  Eigenvectors are conventionally required to be "
        "nonzero so that the eigenvalue is uniquely determined. If v = 0 then id(v) = "
        "lambda * v for every lambda, which would make the eigenvalue ill-defined."
    )
    pdf.section_label("Formal Lean 4 proof")
    pdf.lean_block(
        "theorem eigenvalue_id (v : Fin n -> R) (hv : v != 0) : (fun x : Fin n -> R => x) v = (1 : R) * v",
        "by simp"
    )

    pdf.section_label("Theorem 6")
    pdf.theorem_title("6", "Unity law for scalar multiplication")
    pdf.informal("Statement:  For every vector v in R^n,  1 * v = v.")
    pdf.body(
        "Informal argument.  Multiplying each component by one leaves it unchanged: "
        "(1 * v)(i) = 1 * v(i) = v(i). This is the multiplicative identity law of R "
        "lifted pointwise. The simp tactic closes it using the core simp lemma one_mul."
    )
    pdf.section_label("Formal Lean 4 proof")
    pdf.lean_block(
        "theorem one_smul_vec (v : Fin n -> R) : (1 : R) * v = v",
        "by ext i; simp"
    )

    pdf.ln(2)
    pdf.set_draw_color(*LINE)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(0, 5,
                   "End of proof set. Upload this PDF at leibniz.streamlit.app to "
                   "verify all six theorems against the three gates.")

    pdf.output(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    size = os.path.getsize(path)
    print(f"Generated {path}  ({size:,} bytes)")
