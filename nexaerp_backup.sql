BEGIN TRANSACTION;
CREATE TABLE invoice_items (
	id INTEGER NOT NULL, 
	invoice_id INTEGER NOT NULL, 
	product_name VARCHAR NOT NULL, 
	quantity INTEGER, 
	unit_price FLOAT, 
	total_price FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoices (id)
);
INSERT INTO "invoice_items" VALUES(1,1,'Licence ERP SaaS - Annuelle',1,500000.0,500000.0);
INSERT INTO "invoice_items" VALUES(2,1,'Formation & Intégration',2,75000.0,150000.0);
INSERT INTO "invoice_items" VALUES(3,2,'string',0,0.0,0.0);
INSERT INTO "invoice_items" VALUES(4,3,'string',0,0.0,0.0);
CREATE TABLE invoices (
	id INTEGER NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	doc_type VARCHAR(13) NOT NULL, 
	number VARCHAR NOT NULL, 
	customer_name VARCHAR NOT NULL, 
	customer_email VARCHAR, 
	date DATETIME, 
	due_date DATETIME, 
	status VARCHAR(9), 
	total_ht FLOAT, 
	tax_amount FLOAT, 
	total_ttc FLOAT, 
	language VARCHAR, 
	PRIMARY KEY (id)
);
INSERT INTO "invoices" VALUES(1,'entreprise A','INVOICE','INV-4CA14','SOCIETE TOGO LOGISTIQUE','contact@togologistique.tg','2026-09-24 19:47:37.537556',NULL,'DRAFT',650000.0,117000.0,767000.0,'fr');
INSERT INTO "invoices" VALUES(2,'entreprrise_a','INVOICE','INV-50F53','string','user@example.com','2026-09-28 20:01:34.693939',NULL,'DRAFT',0.0,0.0,0.0,'fr');
INSERT INTO "invoices" VALUES(3,'entreprise_a','INVOICE','INV-1CAEE','string','user@example.com','2026-09-28 20:46:28.057512',NULL,'DRAFT',0.0,0.0,0.0,'fr');
CREATE TABLE permissions (
	id INTEGER NOT NULL, 
	role_id INTEGER NOT NULL, 
	module_name VARCHAR NOT NULL, 
	can_read BOOLEAN, 
	can_create BOOLEAN, 
	can_update BOOLEAN, 
	can_delete BOOLEAN, 
	can_validate BOOLEAN, 
	can_export BOOLEAN, 
	PRIMARY KEY (id), 
	FOREIGN KEY(role_id) REFERENCES roles (id)
);
CREATE TABLE products (
	id INTEGER NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	price FLOAT NOT NULL, 
	quantity INTEGER NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "products" VALUES(1,'sucre','string',0.0,0);
CREATE TABLE roles (
	id INTEGER NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	is_preconfigured BOOLEAN, 
	PRIMARY KEY (id)
);
CREATE TABLE users (
	id INTEGER NOT NULL, 
	tenant_id VARCHAR NOT NULL, 
	email VARCHAR NOT NULL, 
	hashed_password VARCHAR NOT NULL, 
	user_type VARCHAR NOT NULL, 
	role_id INTEGER, 
	is_active BOOLEAN, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_products_id ON products (id);
CREATE INDEX ix_products_tenant_id ON products (tenant_id);
CREATE INDEX ix_users_tenant_id ON users (tenant_id);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_id ON users (id);
CREATE INDEX ix_roles_tenant_id ON roles (tenant_id);
CREATE INDEX ix_roles_id ON roles (id);
CREATE INDEX ix_permissions_id ON permissions (id);
CREATE INDEX ix_invoices_number ON invoices (number);
CREATE INDEX ix_invoices_tenant_id ON invoices (tenant_id);
CREATE INDEX ix_invoices_id ON invoices (id);
CREATE INDEX ix_invoice_items_id ON invoice_items (id);
COMMIT;
