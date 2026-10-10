import json
import os
import re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
MAX_BODY_BYTES = 16_384
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "formula": {"type": "string"},
        "explanation": {"type": "string"},
        "notation": {"type": "string"},
    },
    "required": ["formula", "explanation", "notation"],
    "additionalProperties": False,
}
CELL_REFERENCE = re.compile(r"\$?[A-Za-z]{1,3}\$?\d+")
RANGE_REFERENCE = re.compile(r"(\$?[A-Za-z]{1,3}\$?\d+)\s*:\s*(\$?[A-Za-z]{1,3}\$?\d+)")
LOCAL_FUNCTIONS = {
    "es": {"IF": "SI", "SUM": "SUMA", "AVERAGE": "PROMEDIO", "COUNT": "CONTAR"},
    "en": {"IF": "IF", "SUM": "SUM", "AVERAGE": "AVERAGE", "COUNT": "COUNT"},
}
def local_response(task, text, language):
    if task == "explain":
        if not is_valid_formula(text.strip()):
            return {
                "formula": text.strip(),
                "explanation": (
                    "La fórmula no parece válida: revisa el número de argumentos, los paréntesis y las comillas."
                    if language == "es"
                    else "The formula does not look valid: check its argument count, parentheses, and quotation marks."
                ),
                "notation": "",
                "mode": "local",
                "valid": False,
            }
        explanation = explain_formula_locally(text.strip(), language)
        return {
            "formula": text.strip(),
            "explanation": explanation,
            "notation": formula_to_notation(text.strip(), language),
            "mode": "local",
            "valid": True,
        }

    if is_conditional_format_request(text):
        return {
            "formula": "",
            "explanation": explain_conditional_format_request(text, language),
            "notation": "",
            "mode": "local",
        }

    formula = create_formula_locally(text, language)
    if formula:
        return {
            "formula": formula,
            "explanation": explain_formula_locally(formula, language),
            "notation": formula_to_notation(formula, language),
            "mode": "local",
        }

    explanation = (
        "El modo local todavía no reconoce esa petición. Prueba con una suma, promedio, recuento, "
        "una condición SI/IF con celdas explícitas o activa OPENAI_API_KEY para usar la IA."
        if language == "es"
        else "Local mode does not recognize that request yet. Try a sum, average, count, an IF condition "
        "with explicit cell references, or set OPENAI_API_KEY to use AI."
    )
    return {"formula": "", "explanation": explanation, "notation": "", "mode": "local"}


def is_conditional_format_request(text):
    normalized = text.casefold()
    color_words = ("amarillo", "amarilla", "verde", "rojo", "roja", "azul", "yellow", "green", "red", "blue")
    format_words = (
        "color", "colorea", "colorear", "relleno", "formato", "pinta", "pintar", "ponlo",
        "colour", "color", "fill", "highlight", "make it",
    )
    color_count = sum(normalized.count(word) for word in color_words)
    return color_count > 0 and (
        any(word in normalized for word in format_words)
        or color_count > 1
        or re.search(r"\b(?:es|sea|son|sean|be|is|are)\s+(?:amarill[oa]|verde|rojo|roja|azul|yellow|green|red|blue)\b", normalized)
    )


def explain_conditional_format_request(text, language):
    normalized = text.casefold()
    comparison = parse_comparison(text, language)
    colors = [
        color
        for word, color in (
            ("amarillo", "yellow"),
            ("amarilla", "yellow"),
            ("yellow", "yellow"),
            ("verde", "green"),
            ("green", "green"),
            ("rojo", "red"),
            ("roja", "red"),
            ("red", "red"),
            ("azul", "blue"),
            ("blue", "blue"),
        )
        if word in normalized
    ]
    colors = list(dict.fromkeys(colors))
    if language == "es":
        color_names = {"yellow": "amarillo", "green": "verde", "red": "rojo", "blue": "azul"}
        colors = [color_names[color] for color in colors]
    if language == "es":
        if comparison:
            expression = comparison
            inverse = invert_comparison(comparison)
            if len(colors) >= 2:
                return (
                    "Esto es formato condicional, no una fórmula para el valor de la celda. "
                    f"Selecciona el rango que quieres colorear y crea una regla con la fórmula "
                    f"{expression} para el relleno {colors[0]}, y otra con {inverse} para el relleno "
                    f"{colors[1]}. El complemento aún no aplica los colores automáticamente."
                )
            return (
                "Esto es formato condicional, no una fórmula para el valor de la celda. "
                f"Selecciona el rango que quieres colorear y crea una regla con {expression}; "
                "después elige el color de relleno. El complemento aún no aplica los colores automáticamente."
            )
        return (
            "Esto es formato condicional, no una fórmula para el valor de la celda. Indica las celdas "
            "que se deben comparar (por ejemplo, A1 y B1) y el rango que quieres colorear. "
            "El complemento aún no aplica los colores automáticamente."
        )
    if comparison:
        if len(colors) >= 2:
            return (
                "This is conditional formatting, not a formula for a cell value. Select the range to "
                f"format and create a rule with {comparison} for the {colors[0]} fill, then another "
                f"with {invert_comparison(comparison)} for the {colors[1]} fill. The add-in does not "
                "apply the colors automatically yet."
            )
        return (
            "This is conditional formatting, not a formula for a cell value. Select the range to "
            f"format and create a rule with {comparison}, then choose the fill color. The add-in does "
            "not apply the color automatically yet."
        )
    return (
        "This is conditional formatting, not a formula for a cell value. Specify which cells to "
        "(for example, A1 and B1) compare and the range to format. The add-in does not apply colors "
        "automatically yet."
    )


def parse_comparison(text, language):
    cell = r"\$?[A-Za-z]{1,3}\$?\d+"
    column = r"\$?[A-Za-z]{1,3}"
    value = rf"(?:{cell}|{column}|\d+(?:[.,]\d+)?)"
    direct = re.search(rf"(?<![\w])({value})\s*(<=|>=|<>|=|<|>)\s*({value})(?![\w])", text)
    if direct:
        left, operator, right = direct.groups()
    else:
        spoken_operators = (
            (
                r"(.+?)\s+(?:is\s+)?(greater than or equal to|at least|greater than|more than|exceeds?|above|less than or equal to|at most|less than|below)\s+([\d.,]+|[A-Za-z]{1,3}\d+)",
                {
                    "greater than or equal to": ">=",
                    "at least": ">=",
                    "greater than": ">",
                    "more than": ">",
                    "exceed": ">",
                    "exceeds": ">",
                    "above": ">",
                    "less than or equal to": "<=",
                    "at most": "<=",
                    "less than": "<",
                    "below": "<",
                },
            )
            if language == "en"
            else (
                r"(.+?)\s+(?:es\s+)?(mayor o igual que|mayor que|superior a|superan?|exceden?|menor o igual que|menor que|inferior a)\s+([\d.,]+|[A-Za-z]{1,3}\d+)",
                {
                    "mayor o igual que": ">=",
                    "mayor que": ">",
                    "superior a": ">",
                    "supera": ">",
                    "superan": ">",
                    "excede": ">",
                    "exceden": ">",
                    "menor o igual que": "<=",
                    "menor que": "<",
                    "inferior a": "<",
                },
            )
        )
        spoken_match = re.search(spoken_operators[0], text, re.IGNORECASE)
        if spoken_match:
            left_text, operator_text, right = spoken_match.groups()
            references = CELL_REFERENCE.findall(left_text)
            if not references:
                return None
            left = references[-1]
            operator = spoken_operators[1][operator_text.casefold()]
            right = normalize_number(right, language)
        else:
            words = (
                r"\b(.*?)\s+(?:is\s+)?(greater than or equal to|at least|greater than|more than|less than or equal to|at most|less than|below|above)\s+(.*?)\b"
                if language == "en"
                else r"\b(.*?)\s+(?:es\s+)?(mayor o igual que|mayor que|superior a|menor o igual que|menor que|inferior a)\s+(.*)"
            )
            match = re.search(words, text, re.IGNORECASE)
            if not match:
                return None
            left_text, operator_text, right_text = match.groups()
            left_match = re.search(rf"({value})\s*$", left_text, re.IGNORECASE)
            right_match = re.match(rf"\s*({value})", right_text, re.IGNORECASE)
            if not left_match or not right_match:
                return None
            left, right = left_match.group(1), right_match.group(1)
            operator_key = operator_text.casefold()
            operators = (
                {"greater than or equal to": ">=", "at least": ">=", "greater than": ">", "more than": ">", "less than or equal to": "<=", "at most": "<=", "less than": "<", "below": "<", "above": ">"}
                if language == "en"
                else {"mayor o igual que": ">=", "mayor que": ">", "superior a": ">", "menor o igual que": "<=", "menor que": "<", "inferior a": "<"}
            )
            operator = operators[operator_key]

    left = left.upper()
    right = right.upper()
    if not re.search(r"\d", left):
        left += "1"
    if not re.search(r"\d", right):
        right += "1"
    return f"={left}{operator}{right}"


def normalize_number(value, language):
    value = value.strip().rstrip(".,;")
    if language == "es" and re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value):
        return value.replace(".", "")
    if language == "en" and re.fullmatch(r"\d{1,3}(?:,\d{3})+", value):
        return value.replace(",", "")
    return value.replace(",", ".") if language == "en" else value


def invert_comparison(formula):
    operator_map = {"<": ">=", ">": "<=", "<=": ">", ">=": "<", "=": "<>", "<>": "="}
    match = re.fullmatch(r"(=.+?)(<=|>=|<>|=|<|>)(.+)", formula)
    if not match:
        return formula
    left, operator, right = match.groups()
    return f"{left}{operator_map[operator]}{right}"


def create_formula_locally(text, language):
    normalized = text.casefold()
    functions = LOCAL_FUNCTIONS[language]

    range_match = RANGE_REFERENCE.search(text)
    if not range_match and re.search(r"\b(sum|suma|total|add|sumar)\b", normalized):
        range_match = re.search(
            rf"\b(?:from|de)\s*({CELL_REFERENCE.pattern})\s+(?:to|a)\s*({CELL_REFERENCE.pattern})\b",
            text,
            re.IGNORECASE,
        )
    if range_match:
        excel_range = f"{range_match.group(1).upper()}:{range_match.group(2).upper()}"
        if re.search(r"\b(sum|suma|total|add|sumar)\b", normalized):
            return f"={functions['SUM']}({excel_range})"
        if re.search(r"\b(average|avg|promedio|media)\b", normalized):
            return f"={functions['AVERAGE']}({excel_range})"
        if re.search(r"\b(count|contar|recuento)\b", normalized):
            return f"={functions['COUNT']}({excel_range})"

    if re.search(r"\b(average|avg|promedio|media)\b", normalized):
        return None

    if_condition = re.search(
        r"\bif\s+(.+?)\s+(?:then\s+)?(?:return|show|display)\s+(.+?)\s*(?:;|,|\s)\s*(?:otherwise|else)\s*[,;:]?\s*(.+)$",
        text,
        re.IGNORECASE,
    )
    if language == "es":
        if_condition = if_condition or re.search(
            r"\bsi\s+(.+?)\s+(?:entonces\s+)?(?:devuelve|muestra|da)\s+(.+?)\s*(?:;|,|\s)\s*si no\s*[,;:]?\s*(.+)$",
            text,
            re.IGNORECASE,
        )
    if if_condition:
        condition_text, true_value, false_value = if_condition.groups()
        comparison = parse_comparison(condition_text, language)
        if comparison:
            left, operator, right = re.fullmatch(r"(=.+?)(<=|>=|<>|=|<|>)(.+)", comparison).groups()
            separator = ";" if language == "es" else ","
            return (
                f"={functions['IF']}({left[1:]}{operator}{right}{separator}"
                f"{excel_value(clean_branch_value(true_value), language)}"
                f"{separator}{excel_value(clean_branch_value(false_value), language)})"
            )

    references = CELL_REFERENCE.findall(text)
    if len(references) >= 2 and re.search(r"\b(sum|suma|add|sumar|más|plus)\b", normalized):
        return f"={references[0].upper()}+{references[1].upper()}"

    arithmetic = re.search(rf"(?<![\w])({CELL_REFERENCE.pattern})\s*([+*/-])\s*({CELL_REFERENCE.pattern})(?![\w])", text)
    if arithmetic:
        return f"={arithmetic.group(1).upper()}{arithmetic.group(2)}{arithmetic.group(3).upper()}"
    return None


def excel_value(value, language="en"):
    value = value.strip().strip(" ,;:.“”‘’")
    if re.fullmatch(r"-?\d+(?:[.,]\d+)?", value):
        return normalize_number(value, language)
    if CELL_REFERENCE.fullmatch(value):
        return value.upper()
    if value.casefold() in {"true", "false", "verdadero", "falso"}:
        return value.upper()
    return '"' + value.strip("\"'“”‘’").replace('"', '""') + '"'


def clean_branch_value(value):
    value = value.strip().strip(" ,;:.")
    return re.sub(r"^(?:muestra|devuelve|da|show|display|return)\s+", "", value, flags=re.IGNORECASE)


def explain_formula_locally(formula, language):
    parsed = parse_formula_call(formula)
    if parsed:
        raw_name, args = parsed
        canonical_name = {"SI": "IF", "SUMA": "SUM", "PROMEDIO": "AVERAGE", "CONTAR": "COUNT", "AVERAGE": "AVERAGE"}.get(raw_name.upper(), raw_name.upper())
        if canonical_name == "IF" and len(args) == 3:
            condition = describe_condition(args[0], language)
            true_value = describe_value(args[1], language)
            false_value = describe_value(args[2], language)
            if language == "es":
                return f"Si {condition}, devuelve «{true_value}»; en caso contrario, devuelve «{false_value}»."
            return f"If {condition}, return “{true_value}”; otherwise, return “{false_value}”."
        if canonical_name == "SUM":
            value = args[0] if args else ""
            return f"Suma todos los valores del rango {value}." if language == "es" else f"Adds all values in the {value} range."
        if canonical_name == "AVERAGE":
            value = args[0] if args else ""
            return f"Calcula el promedio de los valores del rango {value}." if language == "es" else f"Calculates the average of values in the {value} range."
        if canonical_name == "COUNT":
            value = args[0] if args else ""
            return f"Cuenta las celdas numéricas del rango {value}." if language == "es" else f"Counts the numeric cells in the {value} range."
        arguments = ", ".join(describe_value(arg, language) for arg in args)
        return f"Aplica {raw_name} a {arguments}." if language == "es" else f"Applies {raw_name} to {arguments}."

    if re.fullmatch(r"=?\s*[A-Za-z]{1,3}\d+\s*(?:<=|>=|<>|=|<|>)\s*[\w.$-]+", formula):
        return describe_condition(formula.lstrip("=").strip(), language)
    arithmetic = re.fullmatch(r"=?\s*(.+?)\s*([+*/-])\s*(.+)", formula)
    if arithmetic:
        left, operator, right = arithmetic.groups()
        words = {
            "+": ("más", "plus"),
            "-": ("menos", "minus"),
            "*": ("multiplicado por", "multiplied by"),
            "/": ("dividido entre", "divided by"),
        }[operator]
        return f"{describe_value(left, language)} {words[0]} {describe_value(right, language)}." if language == "es" else f"{describe_value(left, language)} {words[1]} {describe_value(right, language)}."
    return "No se pudo interpretar esta fórmula como una operación conocida." if language == "es" else "This formula could not be interpreted as a recognized operation."


def formula_to_notation(formula, language):
    parsed = parse_formula_call(formula)
    if parsed:
        raw_name, args = parsed
        canonical_name = {"SI": "IF", "SUMA": "SUM", "PROMEDIO": "AVERAGE", "CONTAR": "COUNT"}.get(raw_name.upper(), raw_name.upper())
        if canonical_name == "IF" and len(args) == 3:
            condition = format_math_expression(args[0].strip())
            true_value = args[1].strip()
            false_value = args[2].strip()
            fallback = "en otro caso" if language == "es" else "otherwise"
            return f"Resultado = ⎧ {true_value}   si {condition}\n             ⎩ {false_value}   {fallback}" if language == "es" else f"Result = ⎧ {true_value}   if {condition}\n           ⎩ {false_value}   {fallback}"
        if canonical_name == "SUM":
            return f"∑ valores({args[0]})" if language == "es" else f"∑ values({args[0]})"
        if canonical_name == "AVERAGE":
            return f"x̄({args[0]})"
        if canonical_name == "COUNT":
            return f"n({args[0]})"
        return f"{raw_name}({'; '.join(args)})"
    expression = formula.strip().lstrip("=")
    return expression.replace("<=", "≤").replace(">=", "≥").replace("<>", "≠").replace("*", " × ").replace("/", " ÷ ")


def parse_formula_call(formula):
    match = re.match(r"^\s*=?\s*([A-Za-zÀ-ÿ.]+)\s*\(", formula)
    if not match:
        return None
    open_index = match.end() - 1
    depth = 0
    in_string = False
    close_index = None
    index = open_index
    while index < len(formula):
        char = formula[index]
        if char == '"':
            if in_string and index + 1 < len(formula) and formula[index + 1] == '"':
                index += 2
                continue
            in_string = not in_string
        elif not in_string and char == "(":
            depth += 1
        elif not in_string and char == ")":
            depth -= 1
            if depth == 0:
                close_index = index
                break
        index += 1
    if close_index is None or formula[close_index + 1:].strip():
        return None
    return match.group(1), split_formula_arguments(formula[open_index + 1:close_index])


def split_formula_arguments(expression):
    args = []
    start = 0
    depth = 0
    in_string = False
    index = 0
    while index < len(expression):
        char = expression[index]
        if char == '"':
            if in_string and index + 1 < len(expression) and expression[index + 1] == '"':
                index += 2
                continue
            in_string = not in_string
        elif not in_string:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char in ";," and depth == 0:
                args.append(expression[start:index].strip())
                start = index + 1
        index += 1
    final_arg = expression[start:].strip()
    if final_arg or args:
        args.append(final_arg)
    return args


def is_valid_formula(formula):
    if not formula.startswith("=") or not formula[1:].strip():
        return False
    depth = 0
    in_string = False
    index = 0
    while index < len(formula):
        char = formula[index]
        if char == '"':
            if in_string and index + 1 < len(formula) and formula[index + 1] == '"':
                index += 2
                continue
            in_string = not in_string
        elif not in_string:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth < 0:
                    return False
        index += 1
    if in_string or depth != 0:
        return False

    parsed = parse_formula_call(formula)
    if parsed:
        name, args = parsed
        canonical_name = {"SI": "IF", "SUMA": "SUM", "PROMEDIO": "AVERAGE", "CONTAR": "COUNT"}.get(name.upper(), name.upper())
        if canonical_name == "IF" and len(args) != 3:
            return False
        if canonical_name in {"SUM", "AVERAGE", "COUNT"} and not args:
            return False
    elif re.match(r"^\s*=?\s*[A-Za-zÀ-ÿ.]+\s*\(", formula):
        return False
    return True


def describe_value(value, language):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1].replace('""', '"')
    if CELL_REFERENCE.fullmatch(value):
        return f"el valor de {value.upper()}" if language == "es" else f"the value in {value.upper()}"
    if RANGE_REFERENCE.fullmatch(value):
        return f"los valores del rango {value.upper()}" if language == "es" else f"the values in range {value.upper()}"
    return value


def describe_condition(condition, language):
    match = re.fullmatch(r"\s*(.+?)\s*(<=|>=|<>|=|<|>)\s*(.+?)\s*", condition)
    if not match:
        return condition.strip()
    left, operator, right = match.groups()
    operator_words = {
        "=": ("es igual a", "equals"),
        "<>": ("es distinto de", "is not equal to"),
        ">": ("es mayor que", "is greater than"),
        "<": ("es menor que", "is less than"),
        ">=": ("es mayor o igual que", "is greater than or equal to"),
        "<=": ("es menor o igual que", "is less than or equal to"),
    }[operator]
    return (
        f"{describe_value(left, language)} {operator_words[0]} {describe_value(right, language)}"
        if language == "es"
        else f"{describe_value(left, language)} {operator_words[1]} {describe_value(right, language)}"
    )


def format_math_expression(expression):
    expression = expression.strip()
    expression = re.sub(r"\s*(<=|>=|<>|=|<|>)\s*", r" \1 ", expression)
    return expression.replace("<=", "≤").replace(">=", "≥").replace("<>", "≠")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path != "/api/generate":
            self.send_json(404, {"error": "Ruta no encontrada."})
            return

        if self.headers.get_content_type() != "application/json":
            self.send_json(415, {"error": "El tipo de contenido debe ser application/json."})
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json(400, {"error": "Longitud de solicitud no válida."})
            return
        if content_length <= 0 or content_length > MAX_BODY_BYTES:
            self.send_json(413, {"error": "La solicitud está vacía o supera el tamaño permitido."})
            return

        try:
            payload = json.loads(self.rfile.read(content_length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(400, {"error": "El cuerpo debe contener JSON válido."})
            return
        if not isinstance(payload, dict):
            self.send_json(400, {"error": "El cuerpo debe ser un objeto JSON."})
            return

        task = payload.get("task")
        text = payload.get("text")
        language = payload.get("language", "es")
        if task not in {"generate", "explain"}:
            self.send_json(400, {"error": "La tarea debe ser generate o explain."})
            return
        if not isinstance(text, str) or not text.strip() or len(text) > 8_000:
            self.send_json(400, {"error": "Escribe una instrucción o fórmula de hasta 8.000 caracteres."})
            return
        if not isinstance(language, str) or language not in {"es", "en"}:
            self.send_json(400, {"error": "El idioma debe ser es o en."})
            return

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self.send_json(200, local_response(task, text, language))
            return

        output_language = "Spanish" if language == "es" else "English"
        if task == "generate":
            if language == "es":
                formula_syntax = (
                    "Use Microsoft Excel Spanish function names (for example, SI, SUMA, Y) and "
                    "semicolons between arguments, as in Spanish Excel. Include a leading equals sign."
                )
            else:
                formula_syntax = (
                    "Use Microsoft Excel English function names and commas between arguments. "
                    "Include a leading equals sign."
                )
            instructions = (
                f"Create one valid Microsoft Excel formula from the user's request. Write the "
                f"explanation and a human-readable mathematical notation in {output_language}. "
                f"{formula_syntax} Do not invent cell references "
                "or column meanings that the user did not provide. If essential details are missing, "
                "ask a concise clarification in explanation and return an empty formula. "
                "Important: if the request asks to change a cell's fill, font, color, or appearance, "
                "do not create an IF formula that returns a text value to imitate formatting. This is "
                "an Excel conditional-formatting rule, not a cell-value formula. This add-in only "
                "inserts formulas and cannot apply formatting. Return an empty formula and explain "
                "that the user must create a rule through Excel's Home/Inicio > Conditional "
                "Formatting/Formato condicional > New Rule/Nueva regla > Use a formula/Usar una "
                "fórmula. Give the rule formula only when its cell references are unambiguous; "
                "otherwise ask which exact cells are being compared. For example, if the user clearly "
                "means A1 compared with B1, the rule can be =A1<B1, and the requested fill color is "
                "selected in the conditional-formatting rule's Format options."
            )
            user_text = f"User request:\n{text}"
        else:
            instructions = (
                "Explain the supplied Excel formula accurately in clear, natural language suitable "
                f"for a professional report. Write the explanation and a readable mathematical "
                f"notation in {output_language}. "
                "Preserve the formula exactly in the formula field. "
                "Do not claim to know the values or result of any cell."
            )
            user_text = f"Excel formula:\n{text}"

        request_body = {
            "model": os.environ.get("OPENAI_MODEL", "gpt-4.1-mini"),
            "instructions": instructions,
            "input": user_text,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "excel_formula_assistant",
                    "strict": True,
                    "schema": RESPONSE_SCHEMA,
                }
            },
        }
        request = Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(request_body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=60) as response:
                openai_response = json.loads(response.read())
            result = self.read_model_result(openai_response)
        except HTTPError as error:
            try:
                error_data = json.loads(error.read())
                message = error_data.get("error", {}).get("message", "Error del servicio de IA.")
            except (json.JSONDecodeError, AttributeError):
                message = "El servicio de IA rechazó la solicitud."
            self.send_json(502, {"error": message})
            return
        except (URLError, TimeoutError):
            self.send_json(502, {"error": "No se pudo conectar con el servicio de IA. Comprueba la conexión."})
            return
        except (AttributeError, json.JSONDecodeError, KeyError, TypeError, ValueError):
            self.send_json(502, {"error": "El servicio de IA devolvió una respuesta que no se pudo interpretar."})
            return

        formula = result.get("formula")
        explanation = result.get("explanation")
        notation = result.get("notation")
        if not isinstance(formula, str) or not isinstance(explanation, str) or not isinstance(notation, str):
            self.send_json(502, {"error": "La respuesta de IA no tiene el formato esperado."})
            return
        if task == "generate" and formula and not formula.lstrip().startswith("="):
            self.send_json(502, {"error": "La respuesta de IA no contiene una fórmula válida de Excel."})
            return
        self.send_json(
            200,
            {
                "formula": formula.strip(),
                "explanation": explanation.strip(),
                "notation": notation.strip(),
                "mode": "ai",
            },
        )

    @staticmethod
    def read_model_result(response):
        if isinstance(response.get("output_text"), str):
            return json.loads(response["output_text"])
        for item in response.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    return json.loads(content["text"])
        raise ValueError("No se encontró texto en la respuesta del modelo.")

    def send_json(self, status, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Servidor listo en http://{host}:{port} (Ctrl+C para detenerlo)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()
