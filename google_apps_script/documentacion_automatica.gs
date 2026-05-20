function doGet(e) {
  try {
    var params = (e && e.parameter) ? e.parameter : {};
    var accion = _leerAccion_(e);

    if (!accion) {
      return _respuestaJson_({
        ok: true,
        mensaje: "Apps Script listo.",
        hojas: _listarHojas_(),
      });
    }

    if (accion === "listarHojas") {
      return _respuestaJson_({
        ok: true,
        hojas: _listarHojas_(),
      });
    }

    if (accion === "ping") {
      return _respuestaJson_({
        ok: true,
        mensaje: "pong",
        hojas: _listarHojas_(),
      });
    }

    if (accion === "ultimasSeries") {
      return _respuestaJson_({
        ok: true,
        hoja: _limpiarTexto_(params.hoja || ""),
        series: obtenerUltimasSeries_(
          _limpiarTexto_(params.hoja || ""),
          parseInt(params.limite || "3", 10)
        ),
      });
    }

    if (accion === "agregarSeriesNuevos") {
      return _respuestaJson_(agregarSeriesNuevos_(params));
    }

    if (accion === "buscarSeriesNuevos") {
      return _respuestaJson_(buscarSeriesNuevos_(params));
    }

    if (accion === "actualizarInfoNuevos") {
      return _respuestaJson_(actualizarInfoNuevos_(params));
    }

    return _respuestaJson_({
      ok: false,
      error: "Accion GET no soportada.",
    });
  } catch (error) {
    return _respuestaJson_({
      ok: false,
      error: String(error && error.message ? error.message : error),
    });
  }
}

function doPost(e) {
  var payload = {};

  try {
    payload = JSON.parse((e && e.postData && e.postData.contents) || "{}");
  } catch (error) {
    return _respuestaJson_({
      ok: false,
      error: "El cuerpo no contiene JSON valido.",
    });
  }

  var accion = String(payload.accion || "").trim();
  if (!accion) {
    return _respuestaJson_({
      ok: false,
      error: "Debes indicar la accion.",
    });
  }

  try {
    if (accion === "registrarDocumentacionAutomatica") {
      return _respuestaJson_(registrarDocumentacionAutomatica_(payload));
    }

    if (accion === "documentarRmaServiceManager") {
      return _respuestaJson_(documentarRmaServiceManager_(payload));
    }

    return _respuestaJson_({
      ok: false,
      error: "Accion POST no soportada.",
    });
  } catch (error) {
    return _respuestaJson_({
      ok: false,
      error: String(error && error.message ? error.message : error),
    });
  }
}

function registrarDocumentacionAutomatica_(payload) {
  var hojaDestino = String(payload.hojaDestino || "").trim();
  var claveUnica = String(payload.claveUnica || "").trim();
  var registros = payload.registros || [];

  if (!hojaDestino) {
    throw new Error("Debes indicar hojaDestino.");
  }
  if (!Array.isArray(registros) || registros.length === 0) {
    throw new Error("Debes enviar al menos un registro.");
  }

  var libro = _obtenerSpreadsheet_();
  var hoja = libro.getSheetByName(hojaDestino);
  if (!hoja) {
    hoja = libro.insertSheet(hojaDestino);
  }

  var encabezados = _resolverEncabezados_(hoja, registros);
  var indicePorClave = claveUnica ? _crearIndicePorClave_(hoja, encabezados, claveUnica) : {};
  var insertados = 0;
  var actualizados = 0;

  registros.forEach(function(registro) {
    var fila = encabezados.map(function(encabezado) {
      return registro[encabezado] == null ? "" : String(registro[encabezado]);
    });

    var valorClave = claveUnica ? String(registro[claveUnica] || "").trim() : "";
    if (claveUnica && valorClave && indicePorClave[valorClave]) {
      hoja.getRange(indicePorClave[valorClave], 1, 1, encabezados.length).setValues([fila]);
      actualizados += 1;
      return;
    }

    hoja.appendRow(fila);
    insertados += 1;
  });

  return {
    ok: true,
    hoja: hojaDestino,
    columnas: encabezados.length,
    procesados: registros.length,
    insertados: insertados,
    actualizados: actualizados,
  };
}

function documentarRmaServiceManager_(payload) {
  var hojaDestino = String(payload.hojaDestino || "RMA").trim();
  var registros = payload.registros || [];
  var defaults = payload.defaults || {};

  if (!Array.isArray(registros) || registros.length === 0) {
    throw new Error("Debes enviar al menos un registro de Service Manager.");
  }

  var libro = _obtenerSpreadsheet_();
  var hoja = libro.getSheetByName(hojaDestino);
  if (!hoja) {
    throw new Error("No existe la hoja destino: " + hojaDestino);
  }

  var encabezados = _leerEncabezados_(hoja);
  if (!encabezados.length) {
    throw new Error("La hoja destino no tiene encabezados en la fila 1.");
  }

  var mapaColumnas = _resolverColumnasRma_(encabezados);
  var filasExistentes = hoja.getLastRow() > 1
    ? hoja.getRange(2, 1, hoja.getLastRow() - 1, encabezados.length).getValues()
    : [];
  var indicePorSerie = _crearIndiceRmaPorSerie_(filasExistentes, mapaColumnas);

  var hoy = Utilities.formatDate(
    new Date(),
    Session.getScriptTimeZone() || "America/Mexico_City",
    "dd/MM/yy"
  );

  var insertados = 0;
  var actualizados = 0;
  var detalles = [];

  registros.forEach(function(registro, posicion) {
    var normalizado = _normalizarRegistroServiceManager_(registro, defaults, hoy);
    if (!normalizado.serieVieja) {
      detalles.push({
        item: posicion + 1,
        id: normalizado.idConsulta,
        ok: false,
        error: "No se pudo resolver la serie vieja desde Model Old.",
      });
      return;
    }

    var filaExistente = indicePorSerie[normalizado.serieVieja] || 0;
    if (filaExistente) {
      var filaActual = filasExistentes[filaExistente - 2].slice();
      var filaActualizada = _fusionarFilaRma_(filaActual, encabezados, mapaColumnas, normalizado);
      hoja.getRange(filaExistente, 1, 1, encabezados.length).setValues([filaActualizada]);
      filasExistentes[filaExistente - 2] = filaActualizada;
      actualizados += 1;
      detalles.push({
        item: posicion + 1,
        id: normalizado.idConsulta,
        fila: filaExistente,
        accion: "actualizado",
        serie: normalizado.serieVieja,
        serieNueva: normalizado.serieNueva,
        rma: normalizado.rma,
      });
      return;
    }

    var nuevaFila = _construirFilaRma_(encabezados, mapaColumnas, normalizado);
    hoja.appendRow(nuevaFila);
    var nuevaPosicion = hoja.getLastRow();
    filasExistentes.push(nuevaFila);
    indicePorSerie[normalizado.serieVieja] = nuevaPosicion;
    insertados += 1;
    detalles.push({
      item: posicion + 1,
      id: normalizado.idConsulta,
      fila: nuevaPosicion,
      accion: "insertado",
      serie: normalizado.serieVieja,
      serieNueva: normalizado.serieNueva,
      rma: normalizado.rma,
    });
  });

  return {
    ok: true,
    hoja: hojaDestino,
    procesados: registros.length,
    insertados: insertados,
    actualizados: actualizados,
    detalles: detalles,
  };
}

function agregarSeriesNuevos_(params) {
  var hoja = _obtenerHojaRequerida_("NUEVOS");
  var valores = hoja.getDataRange().getDisplayValues();
  if (valores.length === 0) {
    throw new Error("La hoja NUEVOS no tiene encabezados.");
  }

  var encabezados = _construirIndiceEncabezados_(valores[0]);
  var series = _partirLineas_(params.series);
  var agregadas = 0;

  series.forEach(function(serie) {
    hoja.appendRow(_construirFilaNuevos_(params, encabezados, serie));
    agregadas += 1;
  });

  return {
    ok: true,
    hoja: "NUEVOS",
    agregadas: agregadas,
  };
}

function buscarSeriesNuevos_(params) {
  var hoja = _obtenerHojaRequerida_("NUEVOS");
  var valores = hoja.getDataRange().getDisplayValues();
  if (valores.length === 0) {
    throw new Error("La hoja NUEVOS no tiene encabezados.");
  }

  var encabezados = _construirIndiceEncabezados_(valores[0]);
  var indiceSerie = _buscarIndiceEncabezado_(encabezados, ["SERIE"]);
  if (indiceSerie === -1) {
    indiceSerie = 0;
  }

  var seriesBuscadas = _partirLineas_(params.series);
  var registros = [];
  var encontradas = {};

  for (var fila = 1; fila < valores.length; fila += 1) {
    var serieActual = _limpiarTexto_(valores[fila][indiceSerie] || "").toUpperCase();
    if (!serieActual || seriesBuscadas.indexOf(serieActual) === -1) {
      continue;
    }

    encontradas[serieActual] = true;
    registros.push(_extraerRegistroNuevos_(encabezados, valores[fila], fila + 1));
  }

  return {
    ok: true,
    hoja: "NUEVOS",
    registros: registros,
    series_no_encontradas: seriesBuscadas.filter(function(serie) {
      return !encontradas[serie];
    }),
  };
}

function actualizarInfoNuevos_(params) {
  var hoja = _obtenerHojaRequerida_("NUEVOS");
  var valores = hoja.getDataRange().getDisplayValues();
  if (valores.length === 0) {
    throw new Error("La hoja NUEVOS no tiene encabezados.");
  }

  var encabezados = _construirIndiceEncabezados_(valores[0]);
  var indiceSerie = _buscarIndiceEncabezado_(encabezados, ["SERIE"]);
  if (indiceSerie === -1) {
    indiceSerie = 0;
  }

  var series = _partirLineas_(params.series);
  var actualizadas = 0;
  var registros = [];
  var encontradas = {};
  var huboCambios = false;

  for (var fila = 1; fila < valores.length; fila += 1) {
    var serieActual = _limpiarTexto_(valores[fila][indiceSerie] || "").toUpperCase();
    if (series.indexOf(serieActual) === -1) {
      continue;
    }

    encontradas[serieActual] = true;
    _asignarValorFilaConPosicion_(valores[fila], encabezados, ["SERIE"], serieActual, 0);
    _asignarValorFilaConPosicion_(valores[fila], encabezados, ["MODELO"], params.modelo, 1);
    _asignarValorFilaConPosicion_(valores[fila], encabezados, ["MARCA"], params.marca, 2);
    _asignarValorFilaConPosicion_(valores[fila], encabezados, ["CONDICION", "TIPO"], params.condicion, 3);
    _asignarValorFilaConPosicion_(valores[fila], encabezados, ["ESTATUS", "ESTADO"], params.estatus, 5);

    registros.push(_extraerRegistroNuevos_(encabezados, valores[fila], fila + 1));
    actualizadas += 1;
    huboCambios = true;
  }

  if (huboCambios) {
    hoja.getRange(1, 1, valores.length, valores[0].length).setValues(valores);
  }

  return {
    ok: true,
    hoja: "NUEVOS",
    actualizadas: actualizadas,
    registros: registros,
    series_no_encontradas: series.filter(function(serie) {
      return !encontradas[serie];
    }),
  };
}

function obtenerUltimasSeries_(nombreHoja, limite) {
  var hoja = _obtenerHojaRequerida_(nombreHoja);
  var valores = hoja.getDataRange().getDisplayValues();
  if (valores.length < 2) {
    return [];
  }

  var encabezados = _construirIndiceEncabezados_(valores[0]);
  var indiceSerie = _buscarIndiceEncabezado_(encabezados, ["SERIE"]);
  if (indiceSerie === -1) {
    throw new Error("La hoja " + nombreHoja + " no contiene una columna SERIE.");
  }

  var series = [];
  for (var fila = valores.length - 1; fila >= 1; fila -= 1) {
    var serie = _limpiarTexto_(valores[fila][indiceSerie] || "");
    if (!serie) {
      continue;
    }
    series.push(serie);
    if (series.length >= Math.max(1, limite || 3)) {
      break;
    }
  }

  return series;
}

function _normalizarRegistroServiceManager_(registro, defaults, hoy) {
  var idConsulta = String(
    registro.query_id || registro.queryId || registro["Consulta Id"] || registro.Id || registro.id || ""
  ).trim();
  var modelOld = String(
    registro.model_old || registro.modelOld || registro["Model Old"] || ""
  ).trim();
  var serieNueva = String(
    registro.serial_number_new ||
    registro.serialNumberNew ||
    registro["Serial Number New"] ||
    ""
  ).trim().toUpperCase();
  var rma = String(registro.rma || registro.Rma || registro.RMA || "").trim();
  var partes = _separarModeloYSerieVieja_(modelOld);

  return {
    idConsulta: idConsulta,
    modelOld: modelOld,
    modelo: partes.modelo || String(defaults.modelo || "").trim(),
    serieVieja: partes.serieVieja,
    serieNueva: serieNueva,
    rma: rma,
    estatus: String(defaults.estatus || "EN PROCESO").trim(),
    fechaSolicitud: String(defaults.fechaSolicitud || hoy).trim(),
    fechaEntrega: String(defaults.fechaEntrega || "").trim(),
    recibe: String(defaults.recibe || "").trim(),
    lugar: String(defaults.lugar || "").trim(),
  };
}

function _separarModeloYSerieVieja_(modelOld) {
  var limpio = String(modelOld || "").replace(/\s+/g, " ").trim();
  if (!limpio) {
    return { modelo: "", serieVieja: "" };
  }

  var partes = limpio.split(" ");
  if (partes.length === 1) {
    return { modelo: partes[0], serieVieja: "" };
  }

  return {
    modelo: partes[0],
    serieVieja: partes[partes.length - 1].toUpperCase(),
  };
}

function _leerAccion_(e) {
  return String((e && e.parameter && e.parameter.accion) || "").trim();
}

function _obtenerSpreadsheet_() {
  var activa = SpreadsheetApp.getActiveSpreadsheet();
  if (activa) {
    return activa;
  }

  var sheetId = PropertiesService.getScriptProperties().getProperty("SHEET_ID");
  if (!sheetId) {
    throw new Error("No existe Spreadsheet activo ni propiedad SHEET_ID configurada.");
  }
  return SpreadsheetApp.openById(sheetId);
}

function _listarHojas_() {
  return _obtenerSpreadsheet_()
    .getSheets()
    .map(function(hoja) {
      return hoja.getName();
    });
}

function _leerEncabezados_(hoja) {
  if (hoja.getLastRow() < 1 || hoja.getLastColumn() < 1) {
    return [];
  }

  return hoja
    .getRange(1, 1, 1, hoja.getLastColumn())
    .getValues()[0]
    .map(function(valor) {
      return String(valor || "").trim();
    });
}

function _resolverEncabezados_(hoja, registros) {
  var encabezadosActuales = _leerEncabezados_(hoja).filter(function(valor) {
    return valor;
  });

  if (encabezadosActuales.length > 0) {
    return encabezadosActuales;
  }

  var encabezados = Object.keys(registros[0] || {}).map(function(clave) {
    return String(clave || "").trim();
  }).filter(function(valor) {
    return valor;
  });

  if (encabezados.length === 0) {
    throw new Error("No hay columnas validas para documentar.");
  }

  hoja.getRange(1, 1, 1, encabezados.length).setValues([encabezados]);
  return encabezados;
}

function _crearIndicePorClave_(hoja, encabezados, claveUnica) {
  var columnaClave = encabezados.indexOf(claveUnica);
  if (columnaClave < 0 || hoja.getLastRow() < 2) {
    return {};
  }

  var valores = hoja
    .getRange(2, columnaClave + 1, hoja.getLastRow() - 1, 1)
    .getValues();
  var indice = {};

  valores.forEach(function(fila, posicion) {
    var clave = String(fila[0] || "").trim();
    if (clave) {
      indice[clave] = posicion + 2;
    }
  });

  return indice;
}

function _resolverColumnasRma_(encabezados) {
  return {
    modelo: _buscarIndiceEncabezadoLista_(_construirIndiceEncabezadosLista_(encabezados), "MODELO"),
    serie: _buscarIndiceEncabezadoLista_(_construirIndiceEncabezadosLista_(encabezados), "SERIE"),
    rma: _buscarIndiceEncabezadoLista_(_construirIndiceEncabezadosLista_(encabezados), "RMA"),
    tareaCsc: _buscarIndiceEncabezadoLista_(_construirIndiceEncabezadosLista_(encabezados), "TAREA CSC"),
    estatus: _buscarIndiceEncabezadoLista_(_construirIndiceEncabezadosLista_(encabezados), "ESTATUS"),
    fechaSolicitud: _buscarIndiceEncabezadoPorPrefijo_(encabezados, "FECHA DE SOLIC"),
    fechaEntrega: _buscarIndiceEncabezadoPorPrefijo_(encabezados, "FECHA DE"),
    recibe: _buscarIndiceEncabezadoLista_(_construirIndiceEncabezadosLista_(encabezados), "RECIBE"),
    serieNueva: _buscarIndiceEncabezadoLista_(_construirIndiceEncabezadosLista_(encabezados), "SERIE NUEVA"),
    lugar: _buscarIndiceEncabezadoLista_(_construirIndiceEncabezadosLista_(encabezados), "LUGAR"),
  };
}

function _crearIndiceRmaPorSerie_(filas, mapaColumnas) {
  if (mapaColumnas.serie < 0) {
    throw new Error("La hoja RMA no contiene la columna SERIE.");
  }

  var indice = {};
  filas.forEach(function(fila, posicion) {
    var serie = String(fila[mapaColumnas.serie] || "").trim().toUpperCase();
    if (serie) {
      indice[serie] = posicion + 2;
    }
  });
  return indice;
}

function _fusionarFilaRma_(filaActual, encabezados, mapaColumnas, registro) {
  var fila = filaActual.slice();
  while (fila.length < encabezados.length) {
    fila.push("");
  }

  _asignarSiExiste_(fila, mapaColumnas.modelo, registro.modelo);
  _asignarSiExiste_(fila, mapaColumnas.serie, registro.serieVieja);
  _asignarSiExiste_(fila, mapaColumnas.rma, registro.rma);
  _asignarSiExiste_(fila, mapaColumnas.tareaCsc, registro.idConsulta);
  _asignarSiExiste_(fila, mapaColumnas.estatus, registro.estatus);
  _asignarSiExiste_(fila, mapaColumnas.fechaSolicitud, registro.fechaSolicitud);
  _asignarSiExiste_(fila, mapaColumnas.fechaEntrega, registro.fechaEntrega);
  _asignarSiExiste_(fila, mapaColumnas.recibe, registro.recibe);
  _asignarSiExiste_(fila, mapaColumnas.serieNueva, registro.serieNueva);
  _asignarSiExiste_(fila, mapaColumnas.lugar, registro.lugar);

  return fila;
}

function _construirFilaRma_(encabezados, mapaColumnas, registro) {
  var fila = encabezados.map(function() {
    return "";
  });
  return _fusionarFilaRma_(fila, encabezados, mapaColumnas, registro);
}

function _construirFilaNuevos_(params, encabezados, serie) {
  var totalColumnas = _valoresTotalesColumnas_(encabezados);
  totalColumnas = Math.max(totalColumnas, 6);
  var fila = [];
  for (var indice = 0; indice < totalColumnas; indice += 1) {
    fila.push("");
  }

  _asignarValorFilaConPosicion_(fila, encabezados, ["SERIE"], serie, 0);
  _asignarValorFilaConPosicion_(fila, encabezados, ["MODELO"], params.modelo, 1);
  _asignarValorFilaConPosicion_(fila, encabezados, ["MARCA"], params.marca, 2);
  _asignarValorFilaConPosicion_(fila, encabezados, ["CONDICION", "TIPO"], params.condicion, 3);
  _asignarValorFilaConPosicion_(fila, encabezados, ["ESTATUS", "ESTADO"], params.estatus, 5);

  return fila;
}

function _extraerRegistroNuevos_(encabezados, fila, numeroFila) {
  return {
    fila: numeroFila,
    serie: _obtenerValorFilaConPosicion_(encabezados, fila, ["SERIE"], 0),
    modelo: _obtenerValorFilaConPosicion_(encabezados, fila, ["MODELO"], 1),
    marca: _obtenerValorFilaConPosicion_(encabezados, fila, ["MARCA"], 2),
    condicion: _obtenerValorFilaConPosicion_(encabezados, fila, ["CONDICION", "TIPO"], 3),
    estatus: _obtenerValorFilaConPosicion_(encabezados, fila, ["ESTATUS", "ESTADO"], 5),
  };
}

function _construirIndiceEncabezados_(encabezados) {
  var mapa = {};
  encabezados.forEach(function(encabezado, indice) {
    mapa[_normalizarEncabezado_(encabezado)] = indice;
  });
  return mapa;
}

function _construirIndiceEncabezadosLista_(encabezados) {
  var mapa = {};
  encabezados.forEach(function(encabezado, indice) {
    mapa[_normalizarEncabezado_(encabezado)] = indice;
  });
  return mapa;
}

function _buscarIndiceEncabezado_(encabezados, nombres) {
  for (var i = 0; i < nombres.length; i += 1) {
    var clave = _normalizarEncabezado_(nombres[i]);
    if (Object.prototype.hasOwnProperty.call(encabezados, clave)) {
      return encabezados[clave];
    }
  }
  return -1;
}

function _buscarIndiceEncabezadoLista_(encabezados, esperado) {
  var esperadoNormalizado = _normalizarEncabezado_(esperado);
  for (var clave in encabezados) {
    if (Object.prototype.hasOwnProperty.call(encabezados, clave) && clave === esperadoNormalizado) {
      return encabezados[clave];
    }
  }
  return -1;
}

function _buscarIndiceEncabezadoPorPrefijo_(encabezados, esperado) {
  var esperadoNormalizado = _normalizarEncabezado_(esperado);
  for (var i = 0; i < encabezados.length; i += 1) {
    if (_normalizarEncabezado_(encabezados[i]).indexOf(esperadoNormalizado) === 0) {
      return i;
    }
  }
  return -1;
}

function _asignarValorFilaConPosicion_(fila, encabezados, nombres, valor, posicionFallback) {
  var indice = _buscarIndiceEncabezado_(encabezados, nombres);
  if (indice === -1) {
    indice = posicionFallback;
  }
  if (indice < 0 || indice >= fila.length) {
    return;
  }
  fila[indice] = _limpiarTexto_(valor || "");
}

function _obtenerValorFilaConPosicion_(encabezados, fila, nombres, posicionFallback) {
  var indice = _buscarIndiceEncabezado_(encabezados, nombres);
  if (indice === -1) {
    indice = posicionFallback;
  }
  if (indice < 0 || indice >= fila.length) {
    return "";
  }
  return fila[indice] || "";
}

function _valoresTotalesColumnas_(encabezados) {
  var indices = Object.keys(encabezados).map(function(clave) {
    return encabezados[clave];
  });
  if (!indices.length) {
    return 0;
  }
  return Math.max.apply(null, indices) + 1;
}

function _obtenerHojaRequerida_(nombreHoja) {
  var hoja = _obtenerSpreadsheet_().getSheetByName(nombreHoja);
  if (!hoja) {
    throw new Error("No existe la hoja requerida: " + nombreHoja);
  }
  return hoja;
}

function _normalizarEncabezado_(valor) {
  return String(valor || "")
    .trim()
    .toUpperCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ");
}

function _limpiarTexto_(valor) {
  return String(valor || "").trim();
}

function _partirLineas_(valor) {
  return String(valor || "")
    .split(/\r?\n/)
    .map(function(item) { return _limpiarTexto_(item).toUpperCase(); })
    .filter(function(item) { return item; });
}

function _parsearListaPosicional_(valor) {
  var texto = String(valor || "").trim();
  if (!texto) {
    return [];
  }

  if (texto.charAt(0) === "[") {
    try {
      return JSON.parse(texto).map(function(item) {
        return _limpiarTexto_(item || "").toUpperCase();
      });
    } catch (error) {
    }
  }

  return String(valor || "")
    .split(/\r?\n/)
    .map(function(item) { return _limpiarTexto_(item).toUpperCase(); });
}

function _asignarSiExiste_(fila, indice, valor) {
  if (indice < 0) {
    return;
  }
  if (valor == null) {
    return;
  }

  var texto = String(valor).trim();
  if (!texto) {
    return;
  }

  fila[indice] = texto;
}

function _respuestaJson_(objeto) {
  return ContentService
    .createTextOutput(JSON.stringify(objeto))
    .setMimeType(ContentService.MimeType.JSON);
}
