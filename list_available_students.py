from sqlalchemy import create_engine, text
import os

# Get database URL from environment or use default
db_url = os.getenv('DATABASE_URL', 'mysql+pymysql://usebeq_user:usebeq_password_123@localhost/usebeq_portal?charset=utf8mb4')

# Create engine
engine = create_engine(db_url)

print("=" * 80)
print("ESTUDIANTES DISPONIBLES EN LA BASE DE DATOS")
print("=" * 80)

with engine.connect() as conn:
    # Get students with their current enrollment info
    query = text("""
        SELECT DISTINCT TOP 20
            s.al_id,
            s.al_curp,
            s.al_nombre,
            s.al_appat,
            s.al_apmat,
            s.al_estatus,
            g.eg_grado,
            g.eg_grupo,
            g.clavecct,
            g.nombrect,
            g.turno
        FROM dbo.SCE004 s
        LEFT JOIN dbo.SCE006 e ON s.al_id = e.al_id
        LEFT JOIN dbo.SCE002 g ON e.eg_id = g.eg_id
        WHERE s.al_estatus IN ('I', 'A', 'E', 'B')
        AND s.al_curp IS NOT NULL
        AND s.al_curp != ''
        ORDER BY s.al_nombre
    """)
    
    result = conn.execute(query)
    students = result.fetchall()
    
    if students:
        print(f"\nTotal de estudiantes encontrados: {len(students)}\n")
        
        for i, student in enumerate(students, 1):
            al_id, curp, nombre, appat, apmat, estatus, grado, grupo, cct, escuela, turno = student
            
            print(f"{i}. {'-' * 76}")
            print(f"   CURP:      {curp}")
            print(f"   Nombre:    {nombre} {appat} {apmat or ''}")
            print(f"   Estatus:   {estatus}")
            if grado:
                print(f"   Grado:     {grado}° {grupo or ''}")
                print(f"   Escuela:   {escuela}")
                print(f"   CCT:       {cct}")
                print(f"   Turno:     {turno}")
            print()
        
        print("=" * 80)
        print("\nPARA AGREGAR UN ESTUDIANTE, NECESITAS:")
        print("  - CURP del estudiante")
        print("  - Apellido paterno")
        print("  - CCT de la escuela")
        print("  - Grupo")
        print("  - Parentesco (PADRE, MADRE o TUTOR)")
        print("\nEJEMPLO DE USO:")
        if students:
            example = students[0]
            print(f"""
curl -X POST "http://localhost:8000/api/v1/students/add-student" \\
  -H "Authorization: Bearer {{tu_token}}" \\
  -H "Content-Type: application/json" \\
  -d '{{
    "curp": "{example[1]}",
    "apellido": "{example[3]}",
    "cct": "{example[8] or 'CCT_AQUI'}",
    "grupo": "{example[7] or 'A'}",
    "parentesco": "PADRE"
  }}'
            """)
    else:
        print("\n✗ No se encontraron estudiantes en la base de datos")
        print("Verifica que la base de datos esté correctamente configurada")

