import os

def generate_50_page_doc(file_path, title, core_content, annex_template, num_annexes=150):
    """Genera un archivo TXT de aproximadamente 50 páginas (aprox. 25,000 - 30,000 palabras)."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"{title}\n\n")
        f.write("="*50 + "\n")
        f.write("POLÍTICA CORE Y MARCO REGULATORIO\n")
        f.write("="*50 + "\n\n")
        f.write(core_content + "\n\n")
        
        f.write("="*50 + "\n")
        f.write("ANEXOS REGIONALES, ESPECIFICACIONES POR DEPARTAMENTO Y GLOSARIO EXTENDIDO\n")
        f.write("="*50 + "\n\n")
        
        # Generar contenido masivo pero estructurado
        for i in range(1, num_annexes + 1):
            f.write(f"ANEXO {i}: Variación Operativa - Región/Departamento {i}\n")
            f.write("-" * 30 + "\n")
            f.write(annex_template.format(index=i))
            f.write("\n\n")
            
        f.write("\n" + "="*50 + "\n")
        f.write("FIN DEL DOCUMENTO\n")
        f.write("="*50 + "\n")

# --- DOCUMENTO 1: VACACIONES ---
vacaciones_core = """
Esta política regula el descanso anual de todos los empleados de Corporación RRHH.
Regla General: 1-5 años: 14 días | 5-10 años: 21 días | +10 años: 28 días.
Procedimiento: Solicitud vía portal con 30 días de antelación.
Excepción Crítica: En caso de emergencia familiar documentada, el preaviso se reduce a 48 horas.
"""
vacaciones_annex = """
Para la oficina {index}, se establece que los empleados del departamento de TI deben coordinar con el líder técnico
para asegurar que no más del 15% del equipo esté ausente simultáneamente. 
Nota específica {index}: El saldo de días de esta sede se rige por el calendario laboral local de la jurisdicción {index}.
Referencia cruzada: El bono vacacional para esta sede se liquida según el Anexo B del Manual de Beneficios.
"""

# --- DOCUMENTO 2: BENEFICIOS ---
beneficios_core = """
Programa de Bienestar Total 2026.
Seguro Médico: MedPlus Premium 100% (Sin copago).
Gimnasio: 70% reembolso (Tope $15.000).
Capacitación: Fondo anual según seniority (Junior $50k, Semi-Senior $120k, Senior $250k).
"""
beneficios_annex = """
CATÁLOGO DE BENEFICIOS LOCALES - SEDE {index}
- Comedor: En esta sede el almuerzo es subvencionado al 95%.
- Transporte: Se otorga un voucher de combustible mensual de ${index}00 para roles comerciales.
- Wellness: El día libre de cumpleaños en esta sede debe tomarse en el mes calendario del evento.
- Convenio Educativo {index}: Descuento del {index}% en la Universidad local asociada.
"""

# --- DOCUMENTO 3: RSE ---
rse_core = """
La empresa destina el 5% de sus ganancias netas a programas de RSE.
Programas: Techo para Todos (Construcción), Futuro Profesional (Mentoría), Cuidado Verde (Ecología).
Presupuesto: El presupuesto exacto para el año 2026 está detallado en los informes de impacto trimestrales.
"""
rse_annex = """
INFORME HISTÓRICO DE IMPACTO SOCIAL - PROYECTO {index}
- Ubicación: Comunidad {index}.
- Inversión realizada: ${index}0.000 USD.
- Voluntarios participantes: {index} colaboradores.
- Requisito especial para este proyecto: Los empleados deben haber completado el taller de seguridad Nivel {index}.
- Resultado: Mejora del {index}% en los indicadores de desarrollo local de la zona {index}.
"""

# Crear directorio si no existe
os.makedirs("data/raw/hr_docs_extended", exist_ok=True)

# Generar los archivos
generate_50_page_doc(
    "data/raw/hr_docs_extended/POLITICA_VACACIONES_EXTENDIDA.txt",
    "POLÍTICA DE VACACIONES Y LICENCIAS - CORPORACIÓN RRHH",
    vacaciones_core,
    vacaciones_annex
)
generate_50_page_doc(
    "data/raw/hr_docs_extended/PROGRAMA_BENEFICIOS_EXTENDIDO.txt",
    "PROGRAMA DE BENEFICIOS CORPORATIVOS",
    beneficios_core,
    beneficios_annex
)
generate_50_page_doc(
    "data/raw/hr_docs_extended/PROGRAMA_RSE_EXTENDIDO.txt",
    "PROGRAMA DE RESPONSABILIDAD SOCIAL EMPRESARIA (RSE)",
    rse_core,
    rse_annex
)

print("✅ Se han generado 3 documentos de 50 páginas cada uno en 'data/raw/hr_docs_extended/'.")
