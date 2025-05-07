import sqlite3
from datetime import datetime

# Database connection helper
def get_db_connection():
    conn = sqlite3.connect('gallery.db')
    conn.row_factory = sqlite3.Row
    return conn

# Helper function to convert date strings to datetime objects
def convert_date_fields(data, date_fields):
    if data is None:
        return None

    result = dict(data)
    for field in date_fields:
        if field in result and result[field] is not None:
            # If it's already a datetime object, no need to convert
            if isinstance(result[field], datetime):
                continue

            try:
                # Try different date formats
                date_formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d']
                for date_format in date_formats:
                    try:
                        result[field] = datetime.strptime(result[field], date_format)
                        break
                    except ValueError:
                        continue
            except (TypeError):
                # If conversion fails, keep the original value
                pass
    return result

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create admin table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS [admin] (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        site_title TEXT DEFAULT 'Art Commission Gallery',
        setup_complete BOOLEAN DEFAULT 0,
        contact_link TEXT DEFAULT ''
    )
    ''')

    # Create references table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS [references] (
        id INTEGER PRIMARY KEY,
        filename TEXT NOT NULL,
        name TEXT,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        description TEXT,
        public BOOLEAN DEFAULT 1,
        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        watermarked BOOLEAN DEFAULT 0
    )
    ''')

    # Add name column to references table if it doesn't exist
    cursor.execute("PRAGMA table_info([references])")
    columns = cursor.fetchall()
    if not any(column['name'] == 'name' for column in columns):
        cursor.execute('ALTER TABLE [references] ADD COLUMN name TEXT')

    # Add contact_link column to admin table if it doesn't exist
    cursor.execute("PRAGMA table_info([admin])")
    columns = cursor.fetchall()
    if not any(column['name'] == 'contact_link' for column in columns):
        cursor.execute('ALTER TABLE [admin] ADD COLUMN contact_link TEXT DEFAULT ""')

    # Create custom reference links table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS [custom_references] (
        id INTEGER PRIMARY KEY,
        link_id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        creation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create reference-to-custom-link junction table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS [custom_reference_items] (
        id INTEGER PRIMARY KEY,
        custom_ref_id INTEGER NOT NULL,
        reference_id INTEGER NOT NULL,
        FOREIGN KEY (custom_ref_id) REFERENCES [custom_references] (id) ON DELETE CASCADE,
        FOREIGN KEY (reference_id) REFERENCES [references] (id) ON DELETE CASCADE
    )
    ''')

    # Create artists table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS [artists] (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        social_links TEXT,
        notes TEXT
    )
    ''')

    # Create commissions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS [commissions] (
        id INTEGER PRIMARY KEY,
        artist_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        price REAL,
        commission_date TIMESTAMP,
        custom_ref_id INTEGER,
        commission_link TEXT,
        public BOOLEAN DEFAULT 1,
        FOREIGN KEY (artist_id) REFERENCES [artists] (id),
        FOREIGN KEY (custom_ref_id) REFERENCES [custom_references] (id)
    )
    ''')

    # Create commission images table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS [commission_images] (
        id INTEGER PRIMARY KEY,
        commission_id INTEGER NOT NULL,
        filename TEXT NOT NULL,
        display_order INTEGER DEFAULT 0,
        FOREIGN KEY (commission_id) REFERENCES [commissions] (id) ON DELETE CASCADE
    )
    ''')

    conn.commit()
    conn.close()

# Admin related functions
def is_setup_complete():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT setup_complete FROM [admin] LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def get_site_title():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT site_title FROM [admin] LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result['site_title'] if result else 'Art Commission Gallery'

def get_footer_text():
    # Return a fixed string as per requirements
    return 'Made with ❤️ by Fuyucchi'

def get_contact_link():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT contact_link FROM [admin] LIMIT 1')
    result = cursor.fetchone()
    conn.close()
    return result['contact_link'] if result and result['contact_link'] else ''

def complete_setup(username, password, site_title):
    from werkzeug.security import generate_password_hash
    hashed_password = generate_password_hash(password)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO [admin] (username, password, site_title, setup_complete) VALUES (?, ?, ?, 1)',
                  (username, hashed_password, site_title))
    conn.commit()
    conn.close()
    return True

def authenticate_user(username, password):
    from werkzeug.security import check_password_hash

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM [admin] WHERE username = ?', (username,))
    admin = cursor.fetchone()
    conn.close()

    if admin and check_password_hash(admin['password'], password):
        return True
    return False

def update_settings(site_title=None, new_password=None, contact_link=None):
    from werkzeug.security import generate_password_hash

    conn = get_db_connection()
    cursor = conn.cursor()

    if site_title:
        cursor.execute('UPDATE [admin] SET site_title = ?', (site_title,))

    if new_password:
        hashed_password = generate_password_hash(new_password)
        cursor.execute('UPDATE [admin] SET password = ?', (hashed_password,))

    if contact_link is not None:
        cursor.execute('UPDATE [admin] SET contact_link = ?', (contact_link,))

    conn.commit()
    conn.close()
    return True

# Reference related functions
def get_organized_references(include_private=False):
    conn = get_db_connection()
    cursor = conn.cursor()

    if include_private:
        cursor.execute('SELECT * FROM [references] ORDER BY category, subcategory')
    else:
        cursor.execute('SELECT * FROM [references] WHERE public = 1 ORDER BY category, subcategory')

    references = cursor.fetchall()

    # Organize references by category and subcategory
    organized_refs = {}
    for ref in references:
        category = ref['category']
        subcategory = ref['subcategory']

        if category not in organized_refs:
            organized_refs[category] = {}

        if subcategory not in organized_refs[category]:
            organized_refs[category][subcategory] = []

        organized_refs[category][subcategory].append(convert_date_fields(ref, ['upload_date']))

    conn.close()
    return organized_refs

def get_public_references():
    return get_organized_references(include_private=False)

def get_all_references():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM [references] ORDER BY category, subcategory')
    references = [convert_date_fields(row, ['upload_date']) for row in cursor.fetchall()]
    conn.close()
    return references

def get_reference_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT category FROM [references] ORDER BY category')
    categories = [row['category'] for row in cursor.fetchall()]
    conn.close()
    return categories

def get_reference_folders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT subcategory FROM [references] ORDER BY subcategory')
    folders = [row['subcategory'] for row in cursor.fetchall()]
    conn.close()
    return folders

def get_reference_by_id(ref_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM [references] WHERE id = ?', (ref_id,))
    reference = cursor.fetchone()
    conn.close()
    if reference:
        return convert_date_fields(reference, ['upload_date'])
    return None

def add_reference(filename, name, category, subcategory, description, public, watermarked):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO [references] (filename, name, category, subcategory, description, public, watermarked)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (filename, name, category, subcategory, description, public, watermarked))
    ref_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ref_id

def update_reference(ref_id, name, category, subcategory, description, public):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE [references] 
        SET name = ?, category = ?, subcategory = ?, description = ?, public = ?
        WHERE id = ?
    ''', (name, category, subcategory, description, public, ref_id))
    conn.commit()
    conn.close()
    return True

def delete_reference(ref_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT filename FROM [references] WHERE id = ?', (ref_id,))
    result = cursor.fetchone()

    if result:
        cursor.execute('DELETE FROM [references] WHERE id = ?', (ref_id,))
        conn.commit()
        conn.close()
        return result['filename']

    conn.close()
    return None

# Custom reference related functions
def get_custom_references():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM [custom_references] ORDER BY creation_date DESC')
    custom_refs = cursor.fetchall()

    # Get count of references for each custom reference
    for i, ref in enumerate(custom_refs):
        cursor.execute('''
            SELECT COUNT(*) as count FROM [custom_reference_items]
            WHERE custom_ref_id = ?
        ''', (ref['id'],))
        count = cursor.fetchone()['count']
        custom_refs[i] = convert_date_fields(ref, ['creation_date'])
        custom_refs[i]['ref_count'] = count

    conn.close()
    return custom_refs

def get_custom_reference_by_link_id(link_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM [custom_references] WHERE link_id = ?', (link_id,))
    custom_ref = cursor.fetchone()
    conn.close()
    if custom_ref:
        return convert_date_fields(custom_ref, ['creation_date'])
    return None

def get_custom_reference_by_id(custom_ref_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM [custom_references] WHERE id = ?', (custom_ref_id,))
    custom_ref = cursor.fetchone()
    conn.close()
    if custom_ref:
        return convert_date_fields(custom_ref, ['creation_date'])
    return None

def get_references_for_custom_ref(custom_ref_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT r.* FROM [references] r
        JOIN custom_reference_items cri ON r.id = cri.reference_id
        WHERE cri.custom_ref_id = ?
    ''', (custom_ref_id,))
    references = [convert_date_fields(row, ['upload_date']) for row in cursor.fetchall()]
    conn.close()
    return references

def create_custom_reference(name, link_id, reference_ids):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create custom reference
    cursor.execute('''
        INSERT INTO [custom_references] (name, link_id)
        VALUES (?, ?)
    ''', (name, link_id))
    custom_ref_id = cursor.lastrowid

    # Add selected references
    for ref_id in reference_ids:
        cursor.execute('''
            INSERT INTO [custom_reference_items] (custom_ref_id, reference_id)
            VALUES (?, ?)
        ''', (custom_ref_id, ref_id))

    conn.commit()
    conn.close()
    return custom_ref_id

def update_custom_reference(custom_ref_id, name, reference_ids):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Update custom reference name
    cursor.execute('''
        UPDATE [custom_references] 
        SET name = ?
        WHERE id = ?
    ''', (name, custom_ref_id))

    # Delete all existing reference items
    cursor.execute('DELETE FROM [custom_reference_items] WHERE custom_ref_id = ?', (custom_ref_id,))

    # Add new selected references
    for ref_id in reference_ids:
        cursor.execute('''
            INSERT INTO [custom_reference_items] (custom_ref_id, reference_id)
            VALUES (?, ?)
        ''', (custom_ref_id, ref_id))

    conn.commit()
    conn.close()
    return True

def delete_custom_reference(custom_ref_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM [custom_references] WHERE id = ?', (custom_ref_id,))
    conn.commit()
    conn.close()
    return True

def get_selected_references_for_custom_ref(custom_ref_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT reference_id FROM [custom_reference_items]
        WHERE custom_ref_id = ?
    ''', (custom_ref_id,))
    selected_refs = [row['reference_id'] for row in cursor.fetchall()]
    conn.close()
    return selected_refs

# Artist related functions
def get_all_artists():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM [artists] ORDER BY name')
    artists = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return artists

def get_artist_by_id(artist_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM [artists] WHERE id = ?', (artist_id,))
    artist = cursor.fetchone()
    conn.close()
    return dict(artist) if artist else None

def add_artist(name, social_links, notes):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO [artists] (name, social_links, notes)
        VALUES (?, ?, ?)
    ''', (name, social_links, notes))
    artist_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return artist_id

def update_artist(artist_id, name, social_links, notes):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE [artists] 
        SET name = ?, social_links = ?, notes = ?
        WHERE id = ?
    ''', (name, social_links, notes, artist_id))
    conn.commit()
    conn.close()
    return True

def delete_artist(artist_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check if artist has commissions
    cursor.execute('SELECT COUNT(*) FROM [commissions] WHERE artist_id = ?', (artist_id,))
    commission_count = cursor.fetchone()[0]

    if commission_count > 0:
        conn.close()
        return False

    # Delete artist
    cursor.execute('DELETE FROM [artists] WHERE id = ?', (artist_id,))
    conn.commit()
    conn.close()
    return True

# Commission related functions
def get_public_commissions():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all public commissions with artist info
    cursor.execute('''
        SELECT c.*, a.name as artist_name 
        FROM [commissions] c
        JOIN [artists] a ON c.artist_id = a.id
        WHERE c.public = 1
        ORDER BY c.commission_date DESC
    ''')
    commissions = cursor.fetchall()

    # Get the first image for each commission for the thumbnail
    for i, comm in enumerate(commissions):
        cursor.execute('''
            SELECT filename FROM [commission_images] 
            WHERE commission_id = ? 
            ORDER BY display_order LIMIT 1
        ''', (comm['id'],))
        thumbnail = cursor.fetchone()
        commissions[i] = convert_date_fields(comm, ['commission_date'])
        commissions[i]['thumbnail'] = thumbnail['filename'] if thumbnail else None

    conn.close()
    return commissions

def get_all_commissions():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all commissions with artist info
    cursor.execute('''
        SELECT c.*, a.name as artist_name 
        FROM [commissions] c
        JOIN [artists] a ON c.artist_id = a.id
        ORDER BY c.commission_date DESC
    ''')
    commissions = cursor.fetchall()

    # Get the first image for each commission for the thumbnail
    for i, comm in enumerate(commissions):
        cursor.execute('''
            SELECT filename FROM [commission_images] 
            WHERE commission_id = ? 
            ORDER BY display_order LIMIT 1
        ''', (comm['id'],))
        thumbnail = cursor.fetchone()
        commissions[i] = convert_date_fields(comm, ['commission_date'])
        commissions[i]['thumbnail'] = thumbnail['filename'] if thumbnail else None

    conn.close()
    return commissions

def get_commission_by_id(commission_id, public_only=True):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get commission details with artist info
    if public_only:
        cursor.execute('''
            SELECT c.*, a.name as artist_name, a.social_links, cr.link_id as custom_ref_link
            FROM [commissions] c
            JOIN [artists] a ON c.artist_id = a.id
            LEFT JOIN [custom_references] cr ON c.custom_ref_id = cr.id
            WHERE c.id = ? AND c.public = 1
        ''', (commission_id,))
    else:
        cursor.execute('''
            SELECT c.*, a.name as artist_name, a.social_links, cr.link_id as custom_ref_link
            FROM [commissions] c
            JOIN [artists] a ON c.artist_id = a.id
            LEFT JOIN [custom_references] cr ON c.custom_ref_id = cr.id
            WHERE c.id = ?
        ''', (commission_id,))

    commission = cursor.fetchone()

    if not commission:
        conn.close()
        return None

    # Get all images for this commission
    cursor.execute('''
        SELECT * FROM [commission_images] 
        WHERE commission_id = ? 
        ORDER BY display_order
    ''', (commission_id,))
    images = [dict(row) for row in cursor.fetchall()]

    result = convert_date_fields(commission, ['commission_date'])
    result['images'] = images

    conn.close()
    return result

def add_commission(title, artist_id, description, price, commission_date, commission_link, custom_ref_id, public):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO [commissions] (title, artist_id, description, price, commission_date, 
                                commission_link, custom_ref_id, public)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (title, artist_id, description, price, commission_date, 
         commission_link, custom_ref_id, public))
    commission_id = cursor.lastrowid

    conn.commit()
    conn.close()
    return commission_id

def update_commission(commission_id, title, artist_id, description, price, commission_date, commission_link, custom_ref_id, public):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE [commissions] 
        SET title = ?, artist_id = ?, description = ?, price = ?, 
            commission_date = ?, commission_link = ?, custom_ref_id = ?, public = ?
        WHERE id = ?
    ''', (title, artist_id, description, price, commission_date, 
         commission_link, custom_ref_id, public, commission_id))

    conn.commit()
    conn.close()
    return True

def delete_commission(commission_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all images for this commission
    cursor.execute('SELECT filename FROM [commission_images] WHERE commission_id = ?', (commission_id,))
    images = cursor.fetchall()

    # Delete commission (cascade will delete images)
    cursor.execute('DELETE FROM [commissions] WHERE id = ?', (commission_id,))

    conn.commit()
    conn.close()

    return [row['filename'] for row in images]

def add_commission_image(commission_id, filename, display_order):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO [commission_images] (commission_id, filename, display_order)
        VALUES (?, ?, ?)
    ''', (commission_id, filename, display_order))

    image_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return image_id

def delete_commission_image(image_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get image details
    cursor.execute('SELECT commission_id, filename FROM [commission_images] WHERE id = ?', (image_id,))
    result = cursor.fetchone()

    if result:
        # Delete from database
        cursor.execute('DELETE FROM [commission_images] WHERE id = ?', (image_id,))
        conn.commit()
        conn.close()
        return dict(result)

    conn.close()
    return None

def update_commission_image_order(image_orders):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        for image_id, display_order in image_orders:
            cursor.execute('''
                UPDATE [commission_images] 
                SET display_order = ?
                WHERE id = ?
            ''', (display_order, image_id))

        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error updating image order: {e}")
        conn.rollback()
        conn.close()
        return False

# Dashboard related functions
def rename_category(old_category, new_category):
    """
    Rename a category across all references.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE [references] 
        SET category = ?
        WHERE category = ?
    ''', (new_category, old_category))
    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()
    return affected_rows

def rename_subcategory(old_subcategory, new_subcategory, category=None):
    """
    Rename a subcategory across all references.
    If category is provided, only rename subcategories within that category.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if category:
        cursor.execute('''
            UPDATE [references] 
            SET subcategory = ?
            WHERE subcategory = ? AND category = ?
        ''', (new_subcategory, old_subcategory, category))
    else:
        cursor.execute('''
            UPDATE [references] 
            SET subcategory = ?
            WHERE subcategory = ?
        ''', (new_subcategory, old_subcategory))

    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()
    return affected_rows

def get_dashboard_counts():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) as ref_count FROM [references]')
    ref_count = cursor.fetchone()['ref_count']

    cursor.execute('SELECT COUNT(*) as comm_count FROM [commissions]')
    comm_count = cursor.fetchone()['comm_count']

    cursor.execute('SELECT COUNT(*) as artist_count FROM [artists]')
    artist_count = cursor.fetchone()['artist_count']

    cursor.execute('SELECT COUNT(*) as custom_ref_count FROM [custom_references]')
    custom_ref_count = cursor.fetchone()['custom_ref_count']

    conn.close()

    return {
        'ref_count': ref_count,
        'comm_count': comm_count,
        'artist_count': artist_count,
        'custom_ref_count': custom_ref_count
    }
