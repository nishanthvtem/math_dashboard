import io
import math
import base64
import re

from flask import Flask, render_template, request, jsonify


com.temenos
$INSERT I_COMMON

app = Flask(__name__)


# ─────────────────────────── helpers ────────────────────────────

def safe_convert_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ─────────────────────────── routes ─────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── 1. Scientific Calculator ──────────────────────────────────────
@app.route("/api/scientific", methods=["POST"])
def scientific():
    data = request.get_json(force=True)
    operation = data.get("operation", "")
    value = safe_convert_float(data.get("value"))
    value2 = safe_convert_float(data.get("value2"))
    angle_mode = data.get("angle_mode", "deg")  # "deg" or "rad"

    def to_rad(v):
        return math.radians(v) if angle_mode == "deg" else v

    try:
        if operation == "sin":
            result = math.sin(to_rad(value))
        elif operation == "cos":
            result = math.cos(to_rad(value))
        elif operation == "tan":
            result = math.tan(to_rad(value))
        elif operation == "asin":
            r = math.asin(value)
            result = math.degrees(r) if angle_mode == "deg" else r
        elif operation == "acos":
            r = math.acos(value)
            result = math.degrees(r) if angle_mode == "deg" else r
        elif operation == "atan":
            r = math.atan(value)
            result = math.degrees(r) if angle_mode == "deg" else r
        elif operation == "log":
            result = math.log10(value)
        elif operation == "ln":
            result = math.log(value)
        elif operation == "sqrt":
            result = math.sqrt(value)
        elif operation == "square":
            result = value ** 2
        elif operation == "power":
            result = value ** value2
        elif operation == "factorial":
            n = int(value)
            if n < 0:
                raise ValueError("Factorial undefined for negative numbers")
            result = math.factorial(n)
        elif operation == "pi":
            result = math.pi
        elif operation == "e":
            result = math.e
        elif operation == "1/x":
            result = 1 / value
        elif operation == "abs":
            result = abs(value)
        else:
            return jsonify({"error": f"Unknown operation: {operation}"}), 400

        # Round tiny floating-point noise
        if isinstance(result, float):
            result = round(result, 10)
        return jsonify({"result": result})

    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        return jsonify({"error": str(exc)}), 400


# ── 2. Unit Converter ─────────────────────────────────────────────
CONVERSIONS = {
    "length": {
        "base": "m",
        "units": {
            "mm": 0.001, "cm": 0.01, "m": 1, "km": 1000,
            "in": 0.0254, "ft": 0.3048, "yd": 0.9144, "mi": 1609.344,
        },
    },
    "weight": {
        "base": "kg",
        "units": {
            "mg": 1e-6, "g": 0.001, "kg": 1, "t": 1000,
            "oz": 0.0283495, "lb": 0.453592, "st": 6.35029,
        },
    },
    "area": {
        "base": "m2",
        "units": {
            "mm2": 1e-6, "cm2": 1e-4, "m2": 1, "km2": 1e6,
            "in2": 6.4516e-4, "ft2": 0.092903, "yd2": 0.836127,
            "acre": 4046.86, "ha": 10000,
        },
    },
    "volume": {
        "base": "L",
        "units": {
            "mL": 0.001, "L": 1, "m3": 1000, "cm3": 0.001,
            "fl_oz": 0.0295735, "cup": 0.236588, "pt": 0.473176,
            "qt": 0.946353, "gal": 3.78541,
        },
    },
    "speed": {
        "base": "m/s",
        "units": {
            "m/s": 1, "km/h": 1 / 3.6, "mph": 0.44704,
            "ft/s": 0.3048, "knot": 0.514444,
        },
    },
}


@app.route("/api/convert", methods=["POST"])
def convert():
    data = request.get_json(force=True)
    category = data.get("category", "")
    from_unit = data.get("from_unit", "")
    to_unit = data.get("to_unit", "")
    value = safe_convert_float(data.get("value"))

    if value is None:
        return jsonify({"error": "Invalid value"}), 400

    # Temperature handled separately (non-linear)
    if category == "temperature":
        try:
            result = _convert_temperature(value, from_unit, to_unit)
            return jsonify({"result": round(result, 6)})
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    cat = CONVERSIONS.get(category)
    if not cat:
        return jsonify({"error": f"Unknown category: {category}"}), 400

    units = cat["units"]
    if from_unit not in units:
        return jsonify({"error": f"Unknown unit: {from_unit}"}), 400
    if to_unit not in units:
        return jsonify({"error": f"Unknown unit: {to_unit}"}), 400

    base_value = value * units[from_unit]
    result = base_value / units[to_unit]
    return jsonify({"result": round(result, 10)})


def _convert_temperature(value, from_unit, to_unit):
    # Convert to Celsius first
    if from_unit == "C":
        celsius = value
    elif from_unit == "F":
        celsius = (value - 32) * 5 / 9
    elif from_unit == "K":
        celsius = value - 273.15
    else:
        raise ValueError(f"Unknown temperature unit: {from_unit}")

    if to_unit == "C":
        return celsius
    elif to_unit == "F":
        return celsius * 9 / 5 + 32
    elif to_unit == "K":
        return celsius + 273.15
    else:
        raise ValueError(f"Unknown temperature unit: {to_unit}")


# ── 3. Equation Solver ────────────────────────────────────────────
@app.route("/api/solve", methods=["POST"])
def solve():
    import sympy
    data = request.get_json(force=True)
    equation = data.get("equation", "").strip()

    if not equation:
        return jsonify({"error": "No equation provided"}), 400

    try:
        # Allow "lhs = rhs" or just "expr" (assumed = 0)
        if "=" in equation:
            lhs_str, rhs_str = equation.split("=", 1)
            lhs = sympy.sympify(lhs_str.strip())
            rhs = sympy.sympify(rhs_str.strip())
            expr = lhs - rhs
        else:
            expr = sympy.sympify(equation)

        x = sympy.Symbol("x")
        solutions = sympy.solve(expr, x)

        if not solutions:
            return jsonify({"result": "No real solutions found"})

        sol_strings = [str(sympy.nsimplify(s, rational=False)) for s in solutions]
        return jsonify({"result": sol_strings})

    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ── 4. Function Grapher ───────────────────────────────────────────
_ALLOWED_NAMES = {
    "sin", "cos", "tan", "asin", "acos", "atan",
    "sinh", "cosh", "tanh",
    "sqrt", "log", "log10", "log2", "exp", "abs",
    "pi", "e", "x",
}

_SAFE_MATH = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
_SAFE_MATH["abs"] = abs


def _safe_eval(expr_str, x_val):
    """Evaluate a math expression string safely."""
    code = compile(expr_str, "<string>", "eval")
    for name in code.co_names:
        if name not in _ALLOWED_NAMES:
            raise ValueError(f"Name '{name}' is not allowed")
    return eval(code, {"__builtins__": {}}, {**_SAFE_MATH, "x": x_val})


@app.route("/api/graph", methods=["POST"])
def graph():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    data = request.get_json(force=True)
    func_str = data.get("function", "").strip()
    x_min = safe_convert_float(data.get("x_min", -10)) or -10
    x_max = safe_convert_float(data.get("x_max", 10)) or 10

    if not func_str:
        return jsonify({"error": "No function provided"}), 400
    if x_min >= x_max:
        return jsonify({"error": "x_min must be less than x_max"}), 400

    try:
        x_vals = np.linspace(x_min, x_max, 800)
        y_vals = []
        for xv in x_vals:
            try:
                y_vals.append(float(_safe_eval(func_str, float(xv))))
            except Exception:
                y_vals.append(float("nan"))

        y_arr = np.array(y_vals, dtype=float)

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(x_vals, y_arr, linewidth=2, color="#4e79a7")
        ax.axhline(0, color="black", linewidth=0.8)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_xlabel("x")
        ax.set_ylabel("f(x)")
        ax.set_title(f"f(x) = {func_str}")
        ax.grid(True, alpha=0.3)
        ax.set_xlim(x_min, x_max)

        # Clip extreme y values for readability
        finite = y_arr[np.isfinite(y_arr)]
        if len(finite):
            y_center = (finite.max() + finite.min()) / 2
            y_range = max(finite.max() - finite.min(), 1e-6)
            ax.set_ylim(y_center - y_range * 0.6, y_center + y_range * 0.6)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=100)
        plt.close(fig)
        buf.seek(0)
        img_b64 = base64.b64encode(buf.read()).decode("utf-8")

        return jsonify({"image": img_b64})

    except Exception as exc:
        return jsonify({"error": str(exc)}), 400


# ─────────────────────────── main ───────────────────────────────

if __name__ == "__main__":
    app.run(debug=True)
