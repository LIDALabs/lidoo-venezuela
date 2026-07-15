def migrate(cr, version):
    """
    Script de migración para:
    1. Eliminar conceptos de pago duplicados y sin código
    2. Crear las líneas de concepto de pago con tarifas y porcentajes correctos
    """
    # Mapeo de tipos de persona del CSV a IDs del sistema
    type_person_mapping = {
        'PN Residente': 'type_person_l10n_ve_payment_extension',
        'PN No Residente': 'type_person_two_l10n_ve_payment_extension',
        'PJ Domiciliada': 'type_person_three_l10n_ve_payment_extension',
        'PJ No Domiciliada': 'type_person_four_l10n_ve_payment_extension',
        'PJ Empresa Emisora De Radio Domiciliada': 'type_person_seven_l10n_ve_payment_extension',
    }
    
    # Mapeo de tarifas del CSV a IDs del sistema
    tariff_mapping = {
        '3% -(Bs. 1;00)': 'fees_retention_data_substrat_l10n_ve_payment_extension',
        '1% - (Bs. 0;33 )': 'fees_retention_data_substrat_second_l10n_ve_payment_extension',
        '34.00%': 'fees_retention_data_percentage_two_l10n_ve_payment_extension',
        '5.00%': 'fees_retention_data_percentage_one_l10n_ve_payment_extension',
        '2.00%': 'fees_retention_data_l10n_ve_percentage_three_payment_extension',
        '3.00%': 'fees_retention_data_percentage_four_l10n_ve_payment_extension',
        'T - 2(Acumulativo)': 'fees_retention_data_percentage_five_l10n_ve_payment_extension',
    }
    
    # Datos del CSV: concepto, tipo persona, codigo, % base imponible, tarifa, desde
    csv_data = [
        ('002/004 - HONORARIOS PROFESIONALES', 'PN Residente', '2', 100, '3% -(Bs. 1;00)', 0),
        ('002/004 - HONORARIOS PROFESIONALES', 'PN No Residente', '3', 90, '34.00%', 0),
        ('002/004 - HONORARIOS PROFESIONALES', 'PJ Domiciliada', '4', 100, '5.00%', 0),
        ('002/004 - HONORARIOS PROFESIONALES', 'PJ No Domiciliada', '5', 90, 'T - 2(Acumulativo)', 0),
        ('071/072 - GASTOS DE TRANSPORTE (FLETES)', 'PN Residente', '71', 100, '1% - (Bs. 0;33 )', 0),
        ('071/072 - GASTOS DE TRANSPORTE (FLETES)', 'PJ Domiciliada', '72', 100, '3.00%', 0),
        ('053/055 - PAGOS A CONTRATISTAS / SUBCONTRATISTAS', 'PN Residente', '53', 100, '1% - (Bs. 0;33 )', 0),
        ('053/055 - PAGOS A CONTRATISTAS / SUBCONTRATISTAS', 'PN No Residente', '54', 100, '34.00%', 0),
        ('053/055 - PAGOS A CONTRATISTAS / SUBCONTRATISTAS', 'PJ Domiciliada', '55', 100, '2.00%', 0),
        ('053/055 - PAGOS A CONTRATISTAS / SUBCONTRATISTAS', 'PJ No Domiciliada', '56', 100, 'T - 2(Acumulativo)', 0),
        ('061/063 - CANONES DE ARRENDAMIENTO DE BIENES MUEBLES', 'PN Residente', '61', 100, '3% -(Bs. 1;00)', 0),
        ('061/063 - CANONES DE ARRENDAMIENTO DE BIENES MUEBLES', 'PN No Residente', '62', 100, '34.00%', 0),
        ('061/063 - CANONES DE ARRENDAMIENTO DE BIENES MUEBLES', 'PJ Domiciliada', '63', 100, '5.00%', 0),
        ('061/063 - CANONES DE ARRENDAMIENTO DE BIENES MUEBLES', 'PJ No Domiciliada', '64', 100, '5.00%', 0),
        ('057/059 - PAGOS DE ADMINISTRADORES DE BIENES INMUEBLES', 'PN Residente', '57', 100, '3% -(Bs. 1;00)', 0),
        ('057/059 - PAGOS DE ADMINISTRADORES DE BIENES INMUEBLES', 'PN No Residente', '58', 90, '34.00%', 0),
        ('057/059 - PAGOS DE ADMINISTRADORES DE BIENES INMUEBLES', 'PJ Domiciliada', '59', 100, '5.00%', 0),
        ('057/059 - PAGOS DE ADMINISTRADORES DE BIENES INMUEBLES', 'PJ No Domiciliada', '60', 90, 'T - 2(Acumulativo)', 0),
        ('083/084/086 - PUBLICIDAD PROPAGANDA Y CESION DE ESPACIOS', 'PN Residente', '83', 100, '3% -(Bs. 1;00)', 0),
        ('083/084/086 - PUBLICIDAD PROPAGANDA Y CESION DE ESPACIOS', 'PJ Domiciliada', '84', 100, '5.00%', 0),
        ('083/084/086 - PUBLICIDAD PROPAGANDA Y CESION DE ESPACIOS', 'PJ No Domiciliada', '85', 100, '5.00%', 0),
        ('083/084/086 - PUBLICIDAD PROPAGANDA Y CESION DE ESPACIOS', 'PJ Empresa Emisora De Radio Domiciliada', '86', 100, '3.00%', 0),
        ('014/016 - COMISIONES DISTINTAS A REMUNERACIONES', 'PN Residente', '14', 100, '3% -(Bs. 1;00)', 0),
        ('014/016 - COMISIONES DISTINTAS A REMUNERACIONES', 'PN No Residente', '15', 100, '34.00%', 0),
        ('014/016 - COMISIONES DISTINTAS A REMUNERACIONES', 'PJ Domiciliada', '16', 100, '5.00%', 0),
        ('014/016 - COMISIONES DISTINTAS A REMUNERACIONES', 'PJ No Domiciliada', '17', 100, '5.00%', 0),
        ('012 - CLINICAS BUFETES FIRMAS CONTADORES INGENIEROS', 'PN Residente', '12', 100, '3% -(Bs. 1;00)', 0),
        ('073/074 - EMPRESAS DE SEGURO CORRETAJE Y REASEGUROS', 'PN Residente', '73', 100, '3% -(Bs. 1;00)', 0),
        ('073/074 - EMPRESAS DE SEGURO CORRETAJE Y REASEGUROS', 'PJ Domiciliada', '74', 100, '5.00%', 0),
        ('001 - SUELDOS Y SALARIOS', 'PN Residente', '1', 100, '3% -(Bs. 1;00)', 0),
    ]
    
    # Eliminar conceptos viejos (sin códigos en el nombre)
    old_names = [
        'Honorarios Profesionales Pagados a',
        'Gastos de Transporte (Fletes) Pagados a',
        '(Contratista) Ejecución de obras y prestación de servicios en Venezuela pagadas a:',
        'Arrendamiento de bienes muebles pagado a:',
        'Arrendamiento o cesión de uso de bienes inmuebles, pagados al arrendador por personas jurídicas, comunidades o los administradores:',
        'Publicidad, propaganda y venta de espacios pagadas a',
        'Comisiones pagadas a',
    ]
    
    for name in old_names:
        cr.execute(
            """
            DELETE FROM payment_concept_line 
            WHERE payment_concept_id IN (
                SELECT id FROM payment_concept WHERE name = %s
            )
            """,
            (name,)
        )
        cr.execute(
            "DELETE FROM payment_concept WHERE name = %s",
            (name,)
        )
    
    # Eliminar duplicados (conceptos con el mismo nombre, mantener solo el más nuevo)
    cr.execute(
        """
        DELETE FROM payment_concept_line 
        WHERE payment_concept_id IN (
            SELECT id FROM payment_concept 
            WHERE id NOT IN (
                SELECT MAX(id) FROM payment_concept GROUP BY name
            )
        )
        """
    )
    cr.execute(
        """
        DELETE FROM payment_concept 
        WHERE id NOT IN (
            SELECT MAX(id) FROM payment_concept GROUP BY name
        )
        """
    )
    
    # Crear líneas de concepto de pago
    for concept_name, person_type, code, tax_base, tariff_name, pay_from in csv_data:
        # Obtener ID del concepto
        cr.execute("SELECT id FROM payment_concept WHERE name = %s", (concept_name,))
        result = cr.fetchone()
        if not result:
            continue
        concept_id = result[0]
        
        # Obtener ID del tipo de persona
        person_xml_id = type_person_mapping.get(person_type)
        if not person_xml_id:
            continue
        cr.execute(
            "SELECT res_id FROM ir_model_data WHERE module = 'l10n_ve_payment_extension' AND name = %s",
            (person_xml_id,)
        )
        result = cr.fetchone()
        if not result:
            continue
        person_id = result[0]
        
        # Obtener ID de la tarifa
        tariff_xml_id = tariff_mapping.get(tariff_name)
        if not tariff_xml_id:
            continue
        cr.execute(
            "SELECT res_id FROM ir_model_data WHERE module = 'l10n_ve_payment_extension' AND name = %s",
            (tariff_xml_id,)
        )
        result = cr.fetchone()
        if not result:
            continue
        tariff_id = result[0]
        
        # Verificar si ya existe una línea con este código
        cr.execute("SELECT id FROM payment_concept_line WHERE code = %s", (code,))
        existing_line = cr.fetchone()
        
        if existing_line:
            # Actualizar línea existente
            cr.execute(
                """
                UPDATE payment_concept_line 
                SET payment_concept_id = %s, type_person_id = %s, percentage_tax_base = %s, 
                    tariff_id = %s, pay_from = %s
                WHERE id = %s
                """,
                (concept_id, person_id, tax_base, tariff_id, pay_from, existing_line[0])
            )
        else:
            # Crear nueva línea
            cr.execute(
                """
                INSERT INTO payment_concept_line 
                (payment_concept_id, type_person_id, percentage_tax_base, tariff_id, code, pay_from, create_uid, create_date)
                VALUES (%s, %s, %s, %s, %s, %s, 1, NOW())
                """,
                (concept_id, person_id, tax_base, tariff_id, code, pay_from)
            )
