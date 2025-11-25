#!/usr/bin/env python3
"""
Script de validación y limpieza del HTML del whitepaper AION
"""
import re
import json
from html.parser import HTMLParser

class HTMLValidator(HTMLParser):
    """Validador de HTML personalizado"""
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.errors = []
        self.warnings = []
        self.tag_stack = []
        
    def handle_starttag(self, tag, attrs):
        self.tag_stack.append(tag)
        attrs_dict = dict(attrs)
        
        # Registrar IDs
        if 'id' in attrs_dict:
            id_val = attrs_dict['id']
            if id_val in self.ids:
                self.errors.append(f"ID duplicado encontrado: '{id_val}'")
            else:
                self.ids.add(id_val)
    
    def handle_endtag(self, tag):
        if self.tag_stack and self.tag_stack[-1] == tag:
            self.tag_stack.pop()
        else:
            self.warnings.append(f"Posible desbalance de etiquetas: </{tag}>")
    
    def handle_startendtag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if 'id' in attrs_dict:
            id_val = attrs_dict['id']
            if id_val in self.ids:
                self.errors.append(f"ID duplicado encontrado: '{id_val}'")
            else:
                self.ids.add(id_val)

def extract_html_from_file(file_path):
    """Extrae el código HTML del archivo de texto"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Buscar el bloque de código HTML
    pattern = r'```html:.*?\n(.*?)```'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        return match.group(1)
    else:
        raise ValueError("No se encontró código HTML en el archivo")

def clean_html(html_content):
    """Elimina las referencias a los SDKs de Abacus.AI"""
    changes = []
    
    # Eliminar las líneas de SDK
    sdk_patterns = [
        r'<script src="/_sdk/element_sdk\.js" defer></script>\s*\n',
        r'<script src="/_sdk/data_sdk\.js" defer></script>\s*\n'
    ]
    
    cleaned_html = html_content
    for pattern in sdk_patterns:
        if re.search(pattern, cleaned_html):
            cleaned_html = re.sub(pattern, '', cleaned_html)
            changes.append(f"Eliminada línea: {pattern.replace(chr(92)+'s*'+chr(92)+'n', '')}")
    
    return cleaned_html, changes

def validate_intersection_observer(html_content):
    """Valida la implementación del IntersectionObserver"""
    validation_report = {
        "status": "OK",
        "issues": [],
        "notes": []
    }
    
    # Buscar el script del IntersectionObserver
    script_pattern = r'<script>(.*?)</script>'
    scripts = re.findall(script_pattern, html_content, re.DOTALL)
    
    io_script = None
    for script in scripts:
        if 'IntersectionObserver' in script:
            io_script = script
            break
    
    if not io_script:
        validation_report["status"] = "ERROR"
        validation_report["issues"].append("No se encontró implementación de IntersectionObserver")
        return validation_report
    
    # Validar componentes críticos del IntersectionObserver
    checks = {
        "TOC selector": r"document\.querySelectorAll\('#toc a'\)",
        "Sections array": r"sections\s*=",
        "Observer creation": r"new IntersectionObserver",
        "Active class toggle": r"classList\.(add|remove)\('active'\)",
        "Observer observe": r"observer\.observe"
    }
    
    for check_name, pattern in checks.items():
        if not re.search(pattern, io_script):
            validation_report["issues"].append(f"Falta componente: {check_name}")
    
    # Validar opciones del observer
    if 'rootMargin' in io_script and 'threshold' in io_script:
        validation_report["notes"].append("✓ Configuración de rootMargin y threshold presente")
    
    if validation_report["issues"]:
        validation_report["status"] = "WARNING"
    else:
        validation_report["notes"].append("✓ IntersectionObserver implementado correctamente")
    
    return validation_report

def validate_toc_links(html_content):
    """Valida que todos los enlaces del TOC tengan sus secciones correspondientes"""
    issues = []
    
    # Extraer IDs de los enlaces del TOC
    toc_pattern = r'<a href="#([^"]+)">[^<]+</a>'
    toc_links = re.findall(toc_pattern, html_content)
    
    # Extraer todos los IDs en el documento
    id_pattern = r'id="([^"]+)"'
    all_ids = re.findall(id_pattern, html_content)
    
    # Verificar que cada enlace del TOC tiene su ID correspondiente
    for link_id in toc_links:
        if link_id not in all_ids:
            issues.append(f"Enlace TOC apunta a ID inexistente: #{link_id}")
    
    return issues

def validate_css_syntax(html_content):
    """Validación básica de sintaxis CSS"""
    issues = []
    
    # Extraer el bloque de estilos
    style_pattern = r'<style>(.*?)</style>'
    styles = re.findall(style_pattern, html_content, re.DOTALL)
    
    if not styles:
        issues.append("No se encontró bloque <style>")
        return issues
    
    css_content = styles[0]
    
    # Validaciones básicas
    open_braces = css_content.count('{')
    close_braces = css_content.count('}')
    
    if open_braces != close_braces:
        issues.append(f"Desbalance de llaves CSS: {open_braces} abiertas, {close_braces} cerradas")
    
    # Verificar selectores críticos
    critical_selectors = [
        r'\.toc\s*{',
        r'\.toc-item\s+a\.active\s*{',
        r'\.section\s*{',
        r'@media.*prefers-reduced-motion'
    ]
    
    for selector in critical_selectors:
        if not re.search(selector, css_content):
            issues.append(f"Falta selector CSS crítico: {selector}")
    
    return issues

def generate_validation_report(html_content, changes, validator, io_validation, toc_issues, css_issues):
    """Genera el reporte de validación completo"""
    report = []
    
    report.append("# 🔍 REPORTE DE VALIDACIÓN - AION WHITEPAPER")
    report.append("")
    report.append(f"**Fecha:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")
    
    # Sección 1: Cambios realizados
    report.append("## 1. 🛠️ Cambios Realizados")
    report.append("")
    if changes:
        report.append("### Eliminación de SDKs de Abacus.AI")
        for change in changes:
            report.append(f"- ✓ {change}")
        report.append("")
        report.append("**Razón:** Estos SDKs no son necesarios para el despliegue en GitHub Pages.")
    else:
        report.append("- ⚠️ No se encontraron SDKs para eliminar")
    report.append("")
    
    # Sección 2: Validación del IntersectionObserver
    report.append("## 2. 👁️ Validación del IntersectionObserver")
    report.append("")
    report.append(f"**Estado:** {io_validation['status']}")
    report.append("")
    
    if io_validation['notes']:
        for note in io_validation['notes']:
            report.append(f"- {note}")
    
    if io_validation['issues']:
        report.append("")
        report.append("**Problemas detectados:**")
        for issue in io_validation['issues']:
            report.append(f"- ❌ {issue}")
    report.append("")
    
    # Sección 3: Validación de Enlaces TOC
    report.append("## 3. 🔗 Validación de Enlaces del TOC")
    report.append("")
    if toc_issues:
        report.append("**Problemas detectados:**")
        for issue in toc_issues:
            report.append(f"- ❌ {issue}")
    else:
        report.append("- ✓ Todos los enlaces del TOC tienen sus secciones correspondientes")
    report.append("")
    
    # Sección 4: Validación de CSS
    report.append("## 4. 🎨 Validación de CSS")
    report.append("")
    if css_issues:
        report.append("**Problemas detectados:**")
        for issue in css_issues:
            report.append(f"- ⚠️ {issue}")
    else:
        report.append("- ✓ Sintaxis CSS válida")
    report.append("")
    
    # Sección 5: Validación de HTML
    report.append("## 5. 📝 Validación de Estructura HTML")
    report.append("")
    report.append(f"**IDs únicos encontrados:** {len(validator.ids)}")
    report.append("")
    
    if validator.errors:
        report.append("**Errores críticos:**")
        for error in validator.errors:
            report.append(f"- ❌ {error}")
        report.append("")
    
    if validator.warnings:
        report.append("**Advertencias:**")
        for warning in validator.warnings[:5]:  # Limitar a 5 advertencias
            report.append(f"- ⚠️ {warning}")
        if len(validator.warnings) > 5:
            report.append(f"- ... y {len(validator.warnings) - 5} advertencias más")
        report.append("")
    
    if not validator.errors and not validator.warnings:
        report.append("- ✓ Estructura HTML válida")
    report.append("")
    
    # Sección 6: Elementos clave verificados
    report.append("## 6. ✅ Elementos Clave Verificados")
    report.append("")
    
    key_elements = {
        "Favicon": r'<link rel="icon"',
        "Meta viewport": r'<meta name="viewport"',
        "Meta description": r'<meta name="description"',
        "TOC sticky": r'position:\s*sticky',
        "Smooth scroll": r'scroll-behavior:\s*smooth',
        "Accessibility (aria-label)": r'aria-label',
        "Responsive design": r'@media.*max-width',
        "Dark mode": r'@media.*prefers-color-scheme:\s*dark',
        "Print styles": r'@media print'
    }
    
    for element, pattern in key_elements.items():
        if re.search(pattern, html_content):
            report.append(f"- ✓ {element}")
        else:
            report.append(f"- ❌ {element} (no encontrado)")
    report.append("")
    
    # Sección 7: Estado Final
    report.append("## 7. 🎯 Estado Final")
    report.append("")
    
    critical_issues = len(validator.errors) + len(toc_issues) + len([i for i in css_issues if 'Desbalance' in i])
    
    if critical_issues == 0 and io_validation['status'] == 'OK':
        report.append("### ✅ **LISTO PARA DESPLIEGUE**")
        report.append("")
        report.append("El archivo HTML ha pasado todas las validaciones críticas y está listo para ser desplegado en GitHub Pages.")
    else:
        report.append("### ⚠️ **REQUIERE AJUSTES**")
        report.append("")
        report.append(f"Se detectaron {critical_issues} problemas críticos que deben ser resueltos antes del despliegue.")
    
    report.append("")
    report.append("---")
    report.append("")
    report.append("## 📋 Resumen de Archivos")
    report.append("")
    report.append("- **Archivo HTML:** `/home/ubuntu/aion_whitepaper/index.html`")
    report.append("- **Reporte de validación:** `/home/ubuntu/aion_whitepaper/VALIDATION_REPORT.md`")
    report.append("")
    report.append("## 🚀 Próximos Pasos")
    report.append("")
    report.append("1. Revisar el archivo `index.html` en un navegador local")
    report.append("2. Verificar que el TOC resalta correctamente al hacer scroll")
    report.append("3. Probar la responsividad en diferentes dispositivos")
    report.append("4. Desplegar en GitHub Pages")
    report.append("")
    
    return '\n'.join(report)

def main():
    """Función principal"""
    print("🔍 Iniciando validación del whitepaper AION...")
    
    # 1. Extraer HTML del archivo
    print("📖 Extrayendo HTML del archivo...")
    input_file = '/home/ubuntu/Uploads/user_message_2025-10-27_17-18-09.txt'
    html_content = extract_html_from_file(input_file)
    print(f"✓ HTML extraído: {len(html_content)} caracteres")
    
    # 2. Limpiar HTML (eliminar SDKs)
    print("🧹 Limpiando referencias a SDKs...")
    cleaned_html, changes = clean_html(html_content)
    print(f"✓ Limpieza completada: {len(changes)} cambios realizados")
    
    # 3. Validar IntersectionObserver
    print("👁️ Validando IntersectionObserver...")
    io_validation = validate_intersection_observer(cleaned_html)
    print(f"✓ Validación IO: {io_validation['status']}")
    
    # 4. Validar enlaces del TOC
    print("🔗 Validando enlaces del TOC...")
    toc_issues = validate_toc_links(cleaned_html)
    print(f"✓ Enlaces TOC: {len(toc_issues)} problemas detectados")
    
    # 5. Validar CSS
    print("🎨 Validando sintaxis CSS...")
    css_issues = validate_css_syntax(cleaned_html)
    print(f"✓ Validación CSS: {len(css_issues)} problemas detectados")
    
    # 6. Validar HTML con parser
    print("📝 Validando estructura HTML...")
    validator = HTMLValidator()
    validator.feed(cleaned_html)
    print(f"✓ HTML validado: {len(validator.errors)} errores, {len(validator.warnings)} advertencias")
    
    # 7. Guardar archivo HTML limpio
    print("💾 Guardando archivo HTML...")
    output_file = '/home/ubuntu/aion_whitepaper/index.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(cleaned_html)
    print(f"✓ Archivo guardado: {output_file}")
    
    # 8. Generar reporte de validación
    print("📊 Generando reporte de validación...")
    report = generate_validation_report(
        cleaned_html, changes, validator, io_validation, toc_issues, css_issues
    )
    
    report_file = '/home/ubuntu/aion_whitepaper/VALIDATION_REPORT.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"✓ Reporte guardado: {report_file}")
    
    print("")
    print("✅ Proceso completado exitosamente")
    print("")
    print("📂 Archivos generados:")
    print(f"   - {output_file}")
    print(f"   - {report_file}")

if __name__ == '__main__':
    main()
