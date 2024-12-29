from flask import (
    render_template, redirect, url_for, request, flash,
    session, send_file
)
from flask_login import login_required, current_user
from app.dashboard import dashboard
from app.models import Usuario, Producto, Venta
from app import db  # Base de datos
from app.dashboard.forms import UsuarioForm, ProductoForm  # Formularios
from sqlalchemy import func
from datetime import datetime, timedelta
import os
import pandas as pd
from flask import current_app
import tempfile  # Asegúrate de incluir esta línea



@dashboard.route('/')
@login_required
def index():
    """
    Muestra el 'Dashboard' con estadísticas y una gráfica.
    - Si es admin, ve datos globales.
    - Si es trabajador, ve SOLO sus datos.
    """
    # 1) Capturar el filtro (día, semana, mes, año) desde la URL, default 'mes'
    filtro = request.args.get('filtro', 'mes')
    hoy = datetime.now()

    # Determinar fecha_inicio según el filtro
    if filtro == 'dia':
        # Hoy a las 00:00
        fecha_inicio = hoy.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filtro == 'semana':
        # Lunes de la semana actual
        fecha_inicio = hoy - timedelta(days=hoy.weekday())
        fecha_inicio = fecha_inicio.replace(hour=0, minute=0, second=0, microsecond=0)
    elif filtro == 'año':
        # 1 de enero del año actual
        fecha_inicio = hoy.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # 'mes' por defecto
        # 1 del mes actual
        fecha_inicio = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # 2) Verificamos si es admin o no para filtrar datos
    if current_user.es_admin:
        # --- ADMIN => Datos Globales ---
        total_usuarios = Usuario.query.count()             # todos los usuarios
        total_productos = Producto.query.count()           # todos los productos
        
        # Ventas desde fecha_inicio (todas)
        ventas_query = Venta.query.filter(Venta.fecha >= fecha_inicio)
        
        total_ventas = ventas_query.count()                # número de ventas
        ingresos_totales = db.session.query(func.sum(Venta.total)) \
                                      .filter(Venta.fecha >= fecha_inicio) \
                                      .scalar() or 0

        # Stock crítico (ej. productos con stock <= 5)
        stock_critico = Producto.query.filter(Producto.stock <= 5).all()

        # Para la gráfica: agrupar por día/semana/mes (dependiendo).
        # Ejemplo simple: agrupar por fecha (YYYY-MM-DD)
        ventas_por_periodo = ventas_query.with_entities(
            func.strftime('%Y-%m-%d', Venta.fecha).label('fecha'),
            func.sum(Venta.total).label('total')
        ).group_by('fecha').all()

    else:
        # --- TRABAJADOR => Datos Personales ---
        # (Podrías mostrar 0 en total_usuarios, 
        #  o si deseas un conteo de algo personal, lo asignas)
        total_usuarios = 0
        
        # Si deseas mostrar total_productos global, no lo filtres:
        total_productos = Producto.query.count()  # => Trabajador ve cuántos productos hay

        # Filtramos SOLO sus ventas, en el rango
        ventas_query = Venta.query.filter_by(usuario_id=current_user.id) \
                                  .filter(Venta.fecha >= fecha_inicio)

        total_ventas = ventas_query.count()
        ingresos_totales = db.session.query(func.sum(Venta.total)) \
                                     .filter(Venta.usuario_id == current_user.id,
                                             Venta.fecha >= fecha_inicio) \
                                     .scalar() or 0

        # Stock crítico (puedes mostrárselo igual)
        # si quieres que el trabajador también vea stock crítico global, hazlo:
        stock_critico = Producto.query.filter(Producto.stock <= 5).all()
        # o si NO quieres que lo vea, asignas stock_critico = []

        # Gráfica con sus ventas
        ventas_por_periodo = ventas_query.with_entities(
            func.strftime('%Y-%m-%d', Venta.fecha).label('fecha'),
            func.sum(Venta.total).label('total')
        ).group_by('fecha').all()

    # Convertir la query en lista de dict para Chart.js
    ventas_por_periodo = [
        {'fecha': v[0], 'total': float(v[1])} for v in ventas_por_periodo
    ]

    # 3) Renderizar la plantilla
    return render_template(
        'dashboard/dashboard.html',
        user=current_user,
        filtro=filtro,
        total_usuarios=total_usuarios,
        total_productos=total_productos,
        total_ventas=total_ventas,
        ingresos_totales=ingresos_totales,
        stock_critico=stock_critico,
        ventas_por_periodo=ventas_por_periodo
    )


# --- Rutas para Usuarios (solo admin) ---
@dashboard.route('/usuarios')
@login_required
def usuarios():
    if not current_user.es_admin:
        return redirect(url_for('dashboard.index'))
    usuarios = Usuario.query.all()
    form = UsuarioForm()
    return render_template('dashboard/usuarios.html',
                           user=current_user,
                           usuarios=usuarios,
                           form=form)

@dashboard.route('/usuarios/agregar', methods=['POST'])
@login_required
def agregar_usuario():
    if not current_user.es_admin:
        return redirect(url_for('dashboard.index'))

    form = UsuarioForm()
    if form.validate_on_submit():
        nombre = form.nombre.data
        email = form.email.data
        password = form.password.data
        es_admin = form.es_admin.data

        nuevo_usuario = Usuario(nombre=nombre, email=email, es_admin=es_admin)
        nuevo_usuario.set_password(password)
        db.session.add(nuevo_usuario)
        db.session.commit()

        flash('Usuario agregado correctamente.', 'success')
        return redirect(url_for('dashboard.usuarios'))

    flash('Error al agregar usuario.', 'danger')
    return redirect(url_for('dashboard.usuarios'))

@dashboard.route('/usuarios/editar/<int:usuario_id>', methods=['POST'])
@login_required
def editar_usuario(usuario_id):
    if not current_user.es_admin:
        return redirect(url_for('dashboard.index'))

    usuario = Usuario.query.get_or_404(usuario_id)
    usuario.nombre = request.form['nombre']
    usuario.email = request.form['email']
    usuario.es_admin = 'es_admin' in request.form

    nueva_password = request.form.get('password', None)
    if nueva_password:
        usuario.set_password(nueva_password)

    db.session.commit()

    flash('Usuario actualizado correctamente.', 'success')
    return redirect(url_for('dashboard.usuarios'))

@dashboard.route('/usuarios/eliminar/<int:usuario_id>', methods=['POST'])
@login_required
def eliminar_usuario(usuario_id):
    if not current_user.es_admin:
        flash("No tienes permiso para eliminar usuarios.", "danger")
        return redirect(url_for('dashboard.index'))

    usuario = Usuario.query.get_or_404(usuario_id)

    # Verificar si el usuario tiene relaciones que impidan su eliminación
    if usuario.ventas:  # Por ejemplo, si hay un modelo relacionado como 'ventas'
        flash("No se puede eliminar este usuario. Consulta con el administrador.", "danger")
        return redirect(url_for('dashboard.usuarios'))

    try:
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuario eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash("Ocurrió un error al intentar eliminar el usuario. Inténtalo de nuevo.", "danger")

    return redirect(url_for('dashboard.usuarios'))



# --- Rutas para Productos ---
@dashboard.route('/productos')
@login_required
def productos():
    """
    CAMBIO:
    Ahora todos pueden ver la lista de productos;
    solo el admin podrá agregar/editar/eliminar.
    """
    productos = Producto.query.all()
    form = ProductoForm()
    return render_template('dashboard/productos.html',
                           user=current_user,
                           productos=productos,
                           form=form)

@dashboard.route('/productos/agregar', methods=['POST'])
@login_required
def agregar_producto():
    if not current_user.es_admin:
        flash("No tienes permiso para agregar productos.", "danger")
        return redirect(url_for('dashboard.productos'))

    form = ProductoForm()
    if form.validate_on_submit():
        nombre = form.nombre.data
        total_piezas = form.total_piezas.data
        stock = total_piezas
        precio = form.precio.data

        nuevo_producto = Producto(
            nombre=nombre,
            total_piezas=total_piezas,
            stock=stock,
            precio=precio
        )
        db.session.add(nuevo_producto)
        db.session.commit()

        flash('Producto agregado correctamente.', 'success')
        return redirect(url_for('dashboard.productos'))

    flash('Error al agregar producto.', 'danger')
    return redirect(url_for('dashboard.productos'))

@dashboard.route('/productos/editar/<int:producto_id>', methods=['POST'])
@login_required
def editar_producto(producto_id):
    if not current_user.es_admin:
        flash("No tienes permiso para editar productos.", "danger")
        return redirect(url_for('dashboard.productos'))

    producto = Producto.query.get_or_404(producto_id)

    try:
        producto.nombre = request.form['nombre']
        producto.total_piezas = int(request.form['total_piezas'])
        nuevo_stock = int(request.form['stock'])

        # Validar que el stock no exceda el total de piezas
        if nuevo_stock > producto.total_piezas:
            flash('El stock no puede exceder el total de piezas.', 'danger')
            return redirect(url_for('dashboard.productos'))

        producto.stock = nuevo_stock
        producto.precio = float(request.form['precio'])
        db.session.commit()

        flash('Producto actualizado correctamente.', 'success')
    except Exception as e:
        flash(f'Error al actualizar el producto: {str(e)}', 'danger')

    return redirect(url_for('dashboard.productos'))

@dashboard.route('/productos/eliminar/<int:producto_id>', methods=['POST'])
@login_required
def eliminar_producto(producto_id):
    if not current_user.es_admin:
        flash("No tienes permiso para eliminar productos.", "danger")
        return redirect(url_for('dashboard.productos'))

    producto = Producto.query.get_or_404(producto_id)

    # Verificar si el producto tiene ventas asociadas
    if producto.ventas:
        flash("No se puede eliminar este producto. Consulta con el administrador.", "danger")
        return redirect(url_for('dashboard.productos'))

    try:
        db.session.delete(producto)
        db.session.commit()
        flash('Producto eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash("Ocurrió un error al intentar eliminar el producto. Inténtalo de nuevo.", "danger")
    
    return redirect(url_for('dashboard.productos'))



# --- Rutas para Ventas ---
@dashboard.route('/ventas')
@login_required
def ventas():
    """
    CAMBIO:
    El admin ve TODAS las ventas.
    El trabajador ve SOLO sus ventas.
    Ambos pueden registrar ventas (agregar).
    """
    ventas_alertas = session.pop('ventas_alertas', [])
    if current_user.es_admin:
        ventas = Venta.query.all()
    else:
        # Trabajador: solo sus ventas
        ventas = Venta.query.filter_by(usuario_id=current_user.id).all()

    productos = Producto.query.all()
    return render_template('dashboard/ventas.html',
                           user=current_user,
                           ventas=ventas,
                           productos=productos,
                           ventas_alertas=ventas_alertas)


@dashboard.route('/ventas/agregar', methods=['POST'])
@login_required
def agregar_venta():
    """
    Todos pueden registrar ventas (admin/trabajador).
    """
    try:
        producto_id = int(request.form['producto_id'])
        cantidad = int(request.form['cantidad'])

        producto = Producto.query.get_or_404(producto_id)
        if cantidad > producto.stock:
            session['ventas_alertas'] = [{
                'category': 'danger',
                'message': 'No hay suficiente stock disponible.'
            }]
            return redirect(url_for('dashboard.ventas'))

        total = cantidad * producto.precio

        venta = Venta(
            cantidad=cantidad,
            total=total,
            usuario_id=current_user.id,  # Quien hace la venta
            producto_id=producto.id
        )

        producto.actualizar_stock(cantidad)

        db.session.add(venta)
        db.session.commit()

        session['ventas_alertas'] = [{
            'category': 'success',
            'message': 'Venta registrada correctamente.'
        }]
    except Exception as e:
        session['ventas_alertas'] = [{
            'category': 'danger',
            'message': f'Error al registrar la venta: {str(e)}'
        }]

    return redirect(url_for('dashboard.ventas'))

@dashboard.route('/ventas/eliminar/<int:venta_id>', methods=['POST'])
@login_required
def eliminar_venta(venta_id):
    """
    Ambos pueden eliminar una venta, 
    pero en la práctica tal vez quieras permitirlo solo al admin.
    Si deseas, puedes condicionar aquí 
    si la venta pertenece al trabajador actual, etc.
    """
    try:
        venta = Venta.query.get_or_404(venta_id)

        # Si quieres que un trabajador solo pueda eliminar SUS ventas, 
        # podrías hacer:
        if not current_user.es_admin and venta.usuario_id != current_user.id:
            session['ventas_alertas'] = [{
                'category': 'danger',
                'message': 'No puedes eliminar ventas de otros usuarios.'
            }]
            return redirect(url_for('dashboard.ventas'))

        # Devolver stock
        producto = Producto.query.get(venta.producto_id)
        if producto:
            producto.stock += venta.cantidad

        db.session.delete(venta)
        db.session.commit()

        session['ventas_alertas'] = [{
            'category': 'success',
            'message': 'Venta eliminada correctamente.'
        }]
    except Exception as e:
        session['ventas_alertas'] = [{
            'category': 'danger',
            'message': f'Error al eliminar la venta: {str(e)}'
        }]

    return redirect(url_for('dashboard.ventas'))


# --- Rutas para Reportes (solo admin) ---
@dashboard.route('/reportes')
@login_required
def reportes():
    if not current_user.es_admin:
        flash('No tienes acceso a los reportes.', 'danger')
        return redirect(url_for('dashboard.index'))

    usuarios = Usuario.query.all()
    productos = Producto.query.all()

    # Años/meses únicos
    años_disponibles = db.session.query(func.strftime("%Y", Venta.fecha)).distinct().all()
    meses_disponibles = db.session.query(func.strftime("%Y-%m", Venta.fecha)).distinct().all()
    años_disponibles = [a[0] for a in años_disponibles]
    meses_disponibles = [m[0] for m in meses_disponibles]

    reportes_alertas = session.pop('reportes_alertas', [])

    return render_template(
        'dashboard/reportes.html',
        user=current_user,
        usuarios=usuarios,
        productos=productos,
        años_disponibles=años_disponibles,
        meses_disponibles=meses_disponibles,
        reportes_alertas=reportes_alertas
    )

@dashboard.route('/reportes/exportar', methods=['GET'])
@login_required
def exportar_reporte():
    if not current_user.es_admin:
        flash('No tienes acceso a exportar reportes.', 'danger')
        return redirect(url_for('dashboard.reportes'))

    try:
        # Crear un archivo temporal en lugar de usar el escritorio del usuario
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            archivo = tmp.name

        filtro = request.args.get("filtro")
        usuario_id = request.args.get("usuario_id")
        producto_id = request.args.get("producto_id")
        fecha = request.args.get("fecha")
        mes = request.args.get("mes")
        año = request.args.get("año")

        query = Venta.query
        if filtro == "dia" and fecha:
            query = query.filter(func.date(Venta.fecha) == fecha)
        elif filtro == "semana" and fecha:
            inicio_semana = datetime.strptime(fecha, "%Y-%m-%d")
            fin_semana = inicio_semana + timedelta(days=6)
            query = query.filter(Venta.fecha.between(inicio_semana, fin_semana))
        elif filtro == "mes" and mes and año:
            # Asegurarse de que el mes tenga dos dígitos
            mes_formateado = mes.zfill(2)
            query = query.filter(func.strftime("%Y-%m", Venta.fecha) == f"{año}-{mes_formateado}")
        elif filtro == "año" and año:
            query = query.filter(func.strftime("%Y", Venta.fecha) == año)
        elif filtro == "usuario" and usuario_id:
            query = query.filter(Venta.usuario_id == usuario_id)
        elif filtro == "producto" and producto_id:
            query = query.filter(Venta.producto_id == producto_id)

        ventas = query.all()

        data = []
        for venta in ventas:
            data.append({
                "ID Venta": venta.id,
                "Producto": venta.producto.nombre,
                "Cantidad": venta.cantidad,
                "Total ($)": venta.total,
                "Usuario": venta.usuario.nombre,
                "Fecha": venta.fecha.strftime("%Y-%m-%d %H:%M:%S")
            })

        df = pd.DataFrame(data)

        if df.empty:
            session['reportes_alertas'] = [{
                "category": "info",
                "message": "No se encontraron datos para los filtros seleccionados."
            }]
            return redirect(url_for("dashboard.reportes"))

        total_ventas = df["Total ($)"].sum()

        with pd.ExcelWriter(archivo, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="Ventas")

            workbook = writer.book
            worksheet = writer.sheets["Ventas"]

            header_format = workbook.add_format({
                "bold": True,
                "bg_color": "#4CAF50",
                "font_color": "white",
                "border": 1,
                "align": "center",
                "valign": "vcenter"
            })
            cell_format = workbook.add_format({
                "border": 1,
                "align": "center",
                "valign": "vcenter"
            })
            total_format = workbook.add_format({
                "bold": True,
                "num_format": "$#,##0.00",
                "border": 1,
                "align": "center",
                "bg_color": "#FFD700"
            })

            # Escribir los encabezados con formato
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)

            # Ajustar el ancho de las columnas
            for i, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).map(len).max(), len(col)) + 2
                worksheet.set_column(i, i, max_length)

            # Aplicar formato a las celdas
            for row_num in range(1, len(df) + 1):
                worksheet.set_row(row_num, None, cell_format)

            # Escribir el total de ventas dos filas después del último dato
            total_row = len(df) + 2
            worksheet.write(total_row, 0, "Total de Ventas:", header_format)
            worksheet.write(total_row, 1, total_ventas, total_format)

        session['last_report_path'] = archivo

        # Redirige a la página de reportes con el parámetro 'descargado=1'
        return redirect(url_for("dashboard.reportes", descargado=1))

    except Exception as e:
        current_app.logger.error(f"Error al generar el reporte: {str(e)}")
        session['reportes_alertas'] = [{
            "category": "danger",
            "message": f"Error al generar el reporte: {str(e)}"
        }]
        return redirect(url_for("dashboard.reportes"))


@dashboard.route('/descargar_archivo')
@login_required
def descargar_archivo():
    if not current_user.es_admin:
        flash('No tienes acceso.', 'danger')
        return redirect(url_for('dashboard.reportes'))

    archivo = session.get('last_report_path')
    filtro = request.args.get("filtro", "reporte_general")  # Valor predeterminado

    if not archivo or not os.path.exists(archivo):
        flash("No se encontró el archivo de reporte.", "warning")
        return redirect(url_for("dashboard.reportes"))

    # Asignar nombre dinámico según el filtro
    nombre_descarga = f"{filtro}_ventas.xlsx"

    return send_file(archivo, as_attachment=True, download_name=nombre_descarga)
