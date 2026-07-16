def migrate(cr, version):
    """
    Script de migración para asignar conceptos de pago a líneas de retención ISLR antiguas.
    """
    # Mapeo de códigos a conceptos
    code_to_concept = {
        '1': '001 - SUELDOS Y SALARIOS',
        '2': '002/004 - HONORARIOS PROFESIONALES',
        '3': '002/004 - HONORARIOS PROFESIONALES',
        '4': '002/004 - HONORARIOS PROFESIONALES',
        '5': '002/004 - HONORARIOS PROFESIONALES',
        '12': '012 - CLINICAS BUFETES FIRMAS CONTADORES INGENIEROS',
        '14': '014/016 - COMISIONES DISTINTAS A REMUNERACIONES',
        '15': '014/016 - COMISIONES DISTINTAS A REMUNERACIONES',
        '16': '014/016 - COMISIONES DISTINTAS A REMUNERACIONES',
        '17': '014/016 - COMISIONES DISTINTAS A REMUNERACIONES',
        '53': '053/055 - PAGOS A CONTRATISTAS / SUBCONTRATISTAS',
        '54': '053/055 - PAGOS A CONTRATISTAS / SUBCONTRATISTAS',
        '55': '053/055 - PAGOS A CONTRATISTAS / SUBCONTRATISTAS',
        '56': '053/055 - PAGOS A CONTRATISTAS / SUBCONTRATISTAS',
        '57': '057/059 - PAGOS DE ADMINISTRADORES DE BIENES INMUEBLES',
        '58': '057/059 - PAGOS DE ADMINISTRADORES DE BIENES INMUEBLES',
        '59': '057/059 - PAGOS DE ADMINISTRADORES DE BIENES INMUEBLES',
        '60': '057/059 - PAGOS DE ADMINISTRADORES DE BIENES INMUEBLES',
        '61': '061/063 - CANONES DE ARRENDAMIENTO DE BIENES MUEBLES',
        '62': '061/063 - CANONES DE ARRENDAMIENTO DE BIENES MUEBLES',
        '63': '061/063 - CANONES DE ARRENDAMIENTO DE BIENES MUEBLES',
        '64': '061/063 - CANONES DE ARRENDAMIENTO DE BIENES MUEBLES',
        '71': '071/072 - GASTOS DE TRANSPORTE (FLETES)',
        '72': '071/072 - GASTOS DE TRANSPORTE (FLETES)',
        '73': '073/074 - EMPRESAS DE SEGURO CORRETAJE Y REASEGUROS',
        '74': '073/074 - EMPRESAS DE SEGURO CORRETAJE Y REASEGUROS',
        '83': '083/084/086 - PUBLICIDAD PROPAGANDA Y CESION DE ESPACIOS',
        '84': '083/084/086 - PUBLICIDAD PROPAGANDA Y CESION DE ESPACIOS',
        '85': '083/084/086 - PUBLICIDAD PROPAGANDA Y CESION DE ESPACIOS',
        '86': '083/084/086 - PUBLICIDAD PROPAGANDA Y CESION DE ESPACIOS',
    }
    
    # PASO 1: Actualizar nombres de conceptos viejos a nuevos
    old_to_new_names = {
        'Honorarios Profesionales Pagados a': '002/004 - HONORARIOS PROFESIONALES',
        'Gastos de Transporte (Fletes) Pagados a': '071/072 - GASTOS DE TRANSPORTE (FLETES)',
        '(Contratista) Ejecución de obras y prestación de servicios en Venezuela pagadas a:': '053/055 - PAGOS A CONTRATISTAS / SUBCONTRATISTAS',
        'Arrendamiento de bienes muebles pagado a:': '061/063 - CANONES DE ARRENDAMIENTO DE BIENES MUEBLES',
        'Arrendamiento o cesión de uso de bienes inmuebles, pagados al arrendador por personas jurídicas, comunidades o los administradores:': '057/059 - PAGOS DE ADMINISTRADORES DE BIENES INMUEBLES',
        'Publicidad, propaganda y venta de espacios pagadas a': '083/084/086 - PUBLICIDAD PROPAGANDA Y CESION DE ESPACIOS',
        'Comisiones pagadas a': '014/016 - COMISIONES DISTINTAS A REMUNERACIONES',
    }
    
    for old_name, new_name in old_to_new_names.items():
        cr.execute(
            "UPDATE payment_concept SET name = %s WHERE name = %s",
            (new_name, old_name)
        )
    
    # PASO 2: Reasignar líneas de concepto al concepto correcto según el código
    for code, concept_name in code_to_concept.items():
        cr.execute("SELECT id FROM payment_concept WHERE name = %s", (concept_name,))
        result = cr.fetchone()
        if not result:
            continue
        concept_id = result[0]
        
        # Actualizar líneas de concepto existentes
        cr.execute(
            "UPDATE payment_concept_line SET payment_concept_id = %s WHERE code = %s",
            (concept_id, code)
        )
    
    # PASO 3: Asignar concepto de pago a líneas de retención ISLR antiguas que no lo tienen
    # Buscar líneas de retención sin payment_concept_id que sean de tipo ISLR
    cr.execute("""
        UPDATE account_retention_line 
        SET payment_concept_id = (
            SELECT pc.id 
            FROM payment_concept pc 
            WHERE pc.name = '001 - SUELDOS Y SALARIOS'
            LIMIT 1
        )
        WHERE payment_concept_id IS NULL 
        AND retention_id IN (
            SELECT ar.id 
            FROM account_retention ar
            WHERE ar.type_retention = 'islr'
        )
    """)
    
    # PASO 4: Para líneas de retención que tienen payment_concept_id pero el concepto tiene nombre viejo
    for old_name, new_name in old_to_new_names.items():
        cr.execute("""
            UPDATE account_retention_line 
            SET payment_concept_id = (
                SELECT id FROM payment_concept WHERE name = %s LIMIT 1
            )
            WHERE payment_concept_id IN (
                SELECT id FROM payment_concept WHERE name = %s
            )
        """, (new_name, old_name))
