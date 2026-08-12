"""
Generate the big-theorem sample PDF (5 pages): Rank-Nullity, Invertibility,
Determinant multiplicativity, Real symmetric eigenvalues, Cayley-Hamilton.
Mixes informal discussion with formal Lean 4 statements (extractable).

Run:  python app/samples/generate_pdf_big.py
"""

from __future__ import annotations
import os
from fpdf import FPDF  # type: ignore

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "linear_algebra_big_theorems.pdf")

INK = (0, 0, 0)
MUTED = (107, 114, 128)
LINE = (229, 231, 235)


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*MUTED)
        self.cell(0, 6, "LEIBNIZ  ·  LINEAR ALGEBRA - BIG THEOREMS", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*LINE)
        self.line(15, 16, 195, 16)
        self.ln(2)
        self.set_text_color(*INK)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 10, f"Two Mathematicians  ·  Page {self.page_no()}  ·  Leibniz Big Theorem Set", align="C")

    def lbl(self, t):
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*MUTED)
        self.cell(0, 5, t.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(*INK)

    def theorem_title(self, num, name):
        self.set_font("Helvetica", "B", 12)
        self.cell(0, 7, f"{num}.  {name}", new_x="LMARGIN", new_y="NEXT")
        self.ln(1)

    def body(self, t):
        self.set_font("Helvetica", "", 10)
        self.set_text_color(*INK)
        self.multi_cell(0, 5.0, t)
        self.ln(1.2)

    def ital(self, t):
        self.set_font("Helvetica", "I", 10)
        self.multi_cell(0, 5.0, t)
        self.ln(1)

    def lean(self, stmt, proof=""):
        self.set_fill_color(243, 244, 246)
        self.set_draw_color(*LINE)
        self.set_font("Courier", "", 8)
        self.set_x(15)
        self.multi_cell(180, 4.8, stmt, border=1, fill=True)
        if proof:
            self.set_x(15)
            self.multi_cell(180, 4.8, "  " + proof, border=1, fill=True)
        self.ln(2.5)


def build():
    p = PDF()
    p.set_auto_page_break(auto=True, margin=18)
    p.add_page()

    # Cover
    p.set_font("Helvetica", "B", 22)
    p.cell(0, 12, "Linear Algebra", new_x="LMARGIN", new_y="NEXT")
    p.set_font("Helvetica", "B", 16)
    p.cell(0, 9, "Big Theorems", new_x="LMARGIN", new_y="NEXT")
    p.set_font("Helvetica", "I", 11)
    p.set_text_color(*MUTED)
    p.cell(0, 6, "Vector spaces · linear maps · matrices · spectral theory", new_x="LMARGIN", new_y="NEXT")
    p.ln(2)
    p.set_draw_color(*INK)
    p.line(15, 46, 195, 46)
    p.ln(4)
    p.set_text_color(*INK)

    p.body(
        "This five-theorem set spans the core of an undergraduate linear-algebra "
        "course. Each theorem is stated informally, argued in prose, and then "
        "formalised as a Lean 4 statement typed against Mathlib. Upload this PDF "
        "to the Leibniz engine: it scans the statements, formalises the informal "
        "text against the encyclopedia, and runs the three gates (Validity, "
        "Alignment, Reading) on each theorem."
    )
    p.body(
        "The theorems span: rank-nullity, invertibility via the determinant, "
        "multiplicativity of the determinant, reality of eigenvalues of symmetric "
        "matrices, and the Cayley-Hamilton theorem. Each is a landmark result; "
        "formal verification of the full proofs requires Mathlib's machinery."
    )
    p.ln(2)

    # Theorem 1 - Rank-Nullity
    p.lbl("Theorem 1")
    p.theorem_title("1", "The Rank-Nullity Theorem")
    p.ital("Let f : V -> W be a linear map between finite-dimensional vector spaces. Then dim(range f) + dim(kernel f) = dim V.")
    p.body(
        "Argument.  The kernel of f is a subspace of V, and the range (image) is a "
        "subspace of W. By the first isomorphism theorem, V / ker f is isomorphic "
        "to range f. Taking dimensions: dim V = dim(ker f) + dim(V/ker f) = "
        "dim(ker f) + dim(range f). This is the fundamental theorem of linear maps: "
        "it constrains how much information a linear transformation can lose."
    )
    p.body(
        "Consequence.  A linear map on a finite-dimensional space is injective iff "
        "rank f = dim V (full rank), and surjective onto W iff rank f = dim W."
    )
    p.lbl("Formal Lean 4 statement")
    p.lean("theorem rank_nullity (K V W : Type*) [Field K] [AddCommGroup V] [Module K V] [AddCommGroup W] [Module K W] [FiniteDimensional K V] [FiniteDimensional K W] (f : V ->_[K] W) : finrank K (LinearMap.range f) + finrank K (LinearMap.ker f) = finrank K V")

    # Theorem 2 - Invertibility
    p.add_page()
    p.lbl("Theorem 2")
    p.theorem_title("2", "Invertibility via the Determinant")
    p.ital("A square matrix over a field is invertible if and only if its determinant is nonzero.")
    p.body(
        "Argument.  The determinant is a multiplicative homomorphism from the matrix "
        "ring to the field. If A is invertible with inverse B, then det(A)det(B) = "
        "det(I) = 1, so det(A) != 0. Conversely, if det(A) != 0, the classical "
        "adjugate formula gives an explicit inverse: A^{-1} = adj(A)/det(A). This "
        "bridges algebraic invertibility with a single scalar invariant, and is the "
        "theoretical backbone of solving Ax = b via Cramer's rule."
    )
    p.body(
        "Remark.  'Nonsingular', 'invertible', and 'full rank' coincide for square "
        "matrices over a field; each characterisation is useful in different contexts."
    )
    p.lbl("Formal Lean 4 statement")
    p.lean("theorem invertible_iff_det_ne_zero (K : Type*) [Field K] (A : Matrix (Fin n) (Fin n) K) : Invertible A <-> det A <> 0")

    # Theorem 3 - det(AB)
    p.lbl("Theorem 3")
    p.theorem_title("3", "Multiplicativity of the Determinant")
    p.ital("For n x n matrices A and B, det(A * B) = det(A) * det(B).")
    p.body(
        "Argument.  Fix A and consider the map B |-> det(AB)/det(A) (for det(A) != 0). "
        "This map is multilinear and alternating in the columns of B, and sends the "
        "identity to 1; by the uniqueness of the determinant as such a function, it "
        "equals det(B). Hence det(AB) = det(A)det(B). The case det(A) = 0 follows by "
        "continuity / polynomial identity. This is the structural reason the "
        "determinant detects invertibility: it is a ring homomorphism to the field's "
        "multiplicative monoid."
    )
    p.lbl("Formal Lean 4 statement")
    p.lean("theorem det_mul (K : Type*) [Field K] (A B : Matrix (Fin n) (Fin n) K) : det (A * B) = det A * det B")

    # Theorem 4 - symmetric eigenvalues
    p.add_page()
    p.lbl("Theorem 4")
    p.theorem_title("4", "Eigenvalues of a Real Symmetric Matrix are Real")
    p.ital("Every eigenvalue of a real symmetric matrix is a real number.")
    p.body(
        "Argument.  Let A be real symmetric (A = A^T) with eigenpair (lambda, v), "
        "viewed over C. Compute v* A v = lambda ||v||^2 in two ways. Since A is "
        "symmetric and real, v* A v is real, forcing lambda real. Equivalently, a "
        "real symmetric matrix is Hermitian, and Hermitian matrices are "
        "diagonalisable by a unitary with a real spectrum (the spectral theorem). "
        "This is why symmetric matrices govern quadratic forms, second derivatives, "
        "and covariance estimation."
    )
    p.body(
        "Consequence.  Real symmetric matrices admit an orthonormal eigenbasis - the "
        "foundation of principal component analysis and the spectral decomposition."
    )
    p.lbl("Formal Lean 4 statement")
    p.lean("theorem real_symmetric_real_eigenvalues (n : Type*) (A : Matrix n n Real) (hA : A.IsSymm) : forall (lam : Complex), A.HasEigenvalue lam -> lam in Set.range ((^) : Real -> Complex)")

    # Theorem 5 - Cayley-Hamilton
    p.lbl("Theorem 5")
    p.theorem_title("5", "The Cayley-Hamilton Theorem")
    p.ital("Every square matrix satisfies its own characteristic equation: p_A(A) = 0, where p_A(t) = det(tI - A).")
    p.body(
        "Argument.  The characteristic polynomial p_A(t) = det(tI - A) is monic of "
        "degree n. Cayley-Hamilton asserts that substituting the matrix A for the "
        "scalar t annihilates A: p_A(A) = 0. The cleanest proof passes to the "
        "algebraic closure: A is triangularisable, and on a triangular form the "
        "eigenvalues (roots of p_A) lie on the diagonal, so p_A(A) is strictly "
        "upper-triangular nilpotent - hence zero. This underpins the minimal "
        "polynomial, the Jordan form, and matrix exponentials in ODE theory."
    )
    p.body(
        "Significance.  Cayley-Hamilton turns a polynomial identity (det(tI - A)) "
        "into a matrix identity, linking spectral and algebraic structure."
    )
    p.lbl("Formal Lean 4 statement")
    p.lean("theorem cayley_hamilton (K : Type*) [Field K] (A : Matrix (Fin n) (Fin n) K) : A.eval (charpoly A) = 0")

    p.ln(2)
    p.set_draw_color(*LINE)
    p.line(15, p.get_y(), 195, p.get_y())
    p.ln(2)
    p.set_font("Helvetica", "I", 9)
    p.set_text_color(*MUTED)
    p.multi_cell(0, 5,
                 "End of big-theorem set. Upload this PDF at leibniz.streamlit.app "
                 "to scan, formalise, and verify each theorem through the three gates.")

    p.output(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Generated {path}  ({os.path.getsize(path):,} bytes)")
