"""

docker exec -i postgres psql -d sdvp -U odoo -c "SELECT name FROM ir_module_module WHERE state = 'installed';" > sdvp_modules.txt

"""
