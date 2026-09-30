import sqlite3


db_filename = "erp.db"
output_sql_file = "nexaerp_backup.sql"

try:
    conn = sqlite3.connect(db_filename)
    with open(output_sql_file,"w", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    print(f" exportation réussie ! le fichier '{output_sql_file}' a été créé avec succès")
except Exception as e:
    print(f"Erreur lors de l'exportation de la base de données : {e}")
finally:
    if "conn" in locals():
        conn.close()