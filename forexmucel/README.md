# Fórmulas claras para Excel

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
