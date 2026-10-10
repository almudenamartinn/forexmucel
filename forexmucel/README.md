# Fórmulas claras para Excel

**Languages:** Español | [English](#clear-formulas-for-excel)

Complemento local de Excel para generar fórmulas a partir de instrucciones escritas y explicarlas en lenguaje natural. Sin clave de API, usa reglas locales para generar fórmulas comunes. Si `OPENAI_API_KEY` está configurada, usa OpenAI para generar instrucciones más abiertas. Usa los pequeños botones con banderas del encabezado para elegir español o inglés; el ajuste cambia la interfaz, las explicaciones y el formato de fórmulas generadas. En español se generan nombres de función localizados y separadores `;`; en inglés se usan nombres ingleses y comas. Cambiar el idioma invalida el resultado anterior para evitar insertar una fórmula generada con el idioma previo. El botón **Insertar en Excel** escribe la fórmula en la celda seleccionada.

El modo local reconoce, entre otros ejemplos, sumas, promedios, recuentos de rangos y condiciones simples con `SI`/`IF`, referencias explícitas y frases como «las ventas de B2 superan 1.000». Al crear una fórmula, puedes alternar entre su formato de Excel, una explicación en palabras y una notación matemática más legible. Las operaciones no reconocidas piden usar una instrucción compatible o configurar una clave de IA.

La creación local detecta las peticiones de color o formato y no las presenta como fórmulas de valor: Excel aplica esos cambios con **Formato condicional**. Por ejemplo, si se quiere colorear A1 cuando sea menor que B1, la regla es `=A1<B1`; hay que crearla desde **Inicio > Formato condicional > Nueva regla > Usar una fórmula** y escoger el relleno. El complemento no aplica todavía ese formato automáticamente.

## Requisitos

- Python 3.9 o posterior.
- Excel de escritorio compatible con complementos de Office.

## Iniciar el servidor

Desde esta carpeta, arranca el servidor. No necesitas una clave para las fórmulas compatibles con el modo local:

```sh
python3 server.py
```

Para habilitar también la generación con IA, configura una clave de OpenAI y arranca el servidor en esa misma terminal:

```sh
export OPENAI_API_KEY="tu-clave"
python3 server.py
```

El modelo predeterminado es `gpt-4.1-mini`; puedes cambiarlo configurando `OPENAI_MODEL` antes de arrancar.

Mantén el servidor abierto mientras uses el complemento. Si configuras una clave, solo se lee en el servidor y nunca se incluye en la página ni se envía a Excel. El asistente recibe únicamente la instrucción o la fórmula que escribes; no lee el contenido de la hoja.

## Cargar el complemento en Excel para Mac

1. Con el servidor activo, abre Excel y un libro.
2. Selecciona **Insertar > Complementos > Mis complementos** (el nombre puede variar según la versión).
3. Elige **Cargar mi complemento** y selecciona `manifest.xml` de esta carpeta.
4. Abre **Fórmulas claras para Excel** desde la cinta de complementos.
5. Selecciona una celda y usa **Insertar en Excel** para escribir ahí la fórmula.

La página también se puede abrir en `http://localhost:8000` para probar el formato y la interfaz; la inserción directa solo funciona dentro de Excel. El manifiesto está pensado para desarrollo local. Para distribuir el complemento a otras personas, se debe publicar con HTTPS y configurar el despliegue de Office correspondiente.

---

<a id="clear-formulas-for-excel"></a>
# Clear Formulas for Excel

**Languages:** [Español](#fórmulas-claras-para-excel) | English

A local Excel add-in that creates formulas from written instructions and explains them in natural language. Common formulas use local rules and do not require an API key. If `OPENAI_API_KEY` is configured, OpenAI can handle more open-ended requests. Use the small flag buttons in the header to switch between Spanish and English; this changes the interface, explanations, and generated formula syntax. Spanish formulas use localized function names and `;` separators, while English formulas use English function names and commas. Changing the language clears the previous result to help prevent inserting a formula generated for the other locale. **Insert into Excel** writes the formula to the selected cell.

Local mode recognizes common patterns, including sums, averages, range counts, and simple `IF` conditions with explicit cell references, such as “if sales in B2 exceed 1,000.” After generating a formula, you can view it in Excel syntax, as a plain-language explanation, or in more readable mathematical notation. Requests that do not match supported patterns need a compatible instruction or an API key for AI.

Local generation identifies requests to change cell colors or formatting instead of representing them as cell-value formulas. Excel applies those changes through **Conditional Formatting**. For example, to color a cell when A1 is less than B1, the rule is `=A1<B1`; create it through **Home > Conditional Formatting > New Rule > Use a formula** and choose a fill color. The add-in does not apply formatting automatically.

## Requirements

- Python 3.9 or later.
- A desktop version of Excel that supports Office add-ins.

## Start the server

From this folder, start the server. No API key is needed for formulas supported by local mode:

```sh
python3 server.py
```

To enable AI for more open-ended requests, set an OpenAI API key and start the server in the same terminal:

```sh
export OPENAI_API_KEY="your-api-key"
python3 server.py
```

The default model is `gpt-4.1-mini`. You can change it by setting `OPENAI_MODEL` before starting the server.

Keep the server running while using the add-in. If configured, the API key is read only by the server; it is never included in the web page or sent to Excel. The assistant receives only the instruction or formula you enter and does not read worksheet contents.

## Load the add-in in Excel for Mac

1. With the server running, open Excel and a workbook.
2. Select **Insert > Add-ins > My Add-ins** (the wording may vary by Excel version).
3. Choose **Upload My Add-in** and select `manifest.xml` from this folder.
4. Open **Clear Formulas for Excel** from the add-ins ribbon.
5. Select a cell and use **Insert into Excel** to write the formula there.

You can also open `http://localhost:8000` to preview the interface; direct insertion works only when the add-in is opened in Excel. The manifest is intended for local development. To distribute the add-in to others, host it over HTTPS and configure the corresponding Office deployment.
