from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, Response
import os
import secrets
import zipfile
import io
from werkzeug.utils import secure_filename
import db
from datetime import datetime
import uuid
from utils import add_watermark
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

# Add current date to all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Add site title, footer text, and contact link to all templates
@app.context_processor
def inject_site_info():
    return {
        'site_title': db.get_site_title(),
        'footer_text': db.get_footer_text(),
        'contact_link': db.get_contact_link()
    }

# Ensure the required directories exist
os.makedirs('static/uploads/references', exist_ok=True)
os.makedirs('static/uploads/commissions', exist_ok=True)


# Initialize the database on first startup
if not os.path.exists('gallery.db'):
    db.init_db()

# Authentication check
def is_authenticated():
    return session.get('authenticated', False)

# Routes
@app.route('/')
def index():
    if not db.is_setup_complete():
        return redirect(url_for('setup'))

    site_title = db.get_site_title()
    return render_template('index.html', site_title=site_title)

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if db.is_setup_complete():
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        site_title = request.form.get('site_title', 'Art Commission Gallery')

        if not username or not password:
            flash('Username and password are required')
            return redirect(url_for('setup'))

        db.complete_setup(username, password, site_title)
        flash('Setup complete! You can now log in.')
        return redirect(url_for('login'))

    return render_template('setup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_authenticated():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if db.authenticate_user(username, password):
            session['authenticated'] = True
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/references')
def references():
    site_title = db.get_site_title()
    # Show private references if user is logged in
    include_private = is_authenticated()
    organized_refs = db.get_organized_references(include_private=include_private)
    categories = db.get_reference_categories()
    folders = db.get_reference_folders()
    return render_template('references.html', site_title=site_title, references=organized_refs,
                          categories=categories, folders=folders)

@app.route('/custom_reference/<link_id>')
def custom_reference(link_id):
    site_title = db.get_site_title()
    custom_ref = db.get_custom_reference_by_link_id(link_id)

    if not custom_ref:
        flash('Custom reference link not found')
        return redirect(url_for('index'))

    references = db.get_references_for_custom_ref(custom_ref['id'])
    categories = db.get_reference_categories()
    folders = db.get_reference_folders()

    return render_template('custom_reference.html', site_title=site_title,
                          custom_ref=custom_ref, references=references,
                          categories=categories, folders=folders)

@app.route('/commissions')
def commissions():
    site_title = db.get_site_title()
    commissions = db.get_public_commissions()
    return render_template('commissions.html', site_title=site_title, commissions=reversed(commissions))

@app.route('/commission/<int:commission_id>')
def commission_detail(commission_id):
    site_title = db.get_site_title()
    commission = db.get_commission_by_id(commission_id, public_only=True)

    if not commission:
        flash('Commission not found')
        return redirect(url_for('commissions'))

    return render_template('commission_detail.html', site_title=site_title,
                          commission=commission, images=commission['images'])

@app.route('/api/commission/<int:commission_id>')
def api_commission_detail(commission_id):
    commission = db.get_commission_by_id(commission_id, public_only=True)

    if not commission:
        return jsonify({'error': 'Commission not found'}), 404

    # Format the date for JSON response
    if commission['commission_date'] and hasattr(commission['commission_date'], 'strftime'):
        commission['commission_date'] = commission['commission_date'].strftime('%Y-%m-%d')

    return jsonify(commission)

# Dashboard routes (all require authentication)
@app.route('/dashboard')
def dashboard():
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    counts = db.get_dashboard_counts()

    return render_template('dashboard/index.html', site_title=site_title,
                          ref_count=counts['ref_count'],
                          comm_count=counts['comm_count'],
                          artist_count=counts['artist_count'],
                          custom_ref_count=counts['custom_ref_count'])

@app.route('/dashboard/settings', methods=['GET', 'POST'])
def dashboard_settings():
    if not is_authenticated():
        return redirect(url_for('login'))

    if request.method == 'POST':
        site_title = request.form.get('site_title')
        new_password = request.form.get('new_password')
        contact_link = request.form.get('contact_link')

        db.update_settings(site_title, new_password, contact_link)
        flash('Settings updated successfully')

    site_title = db.get_site_title()
    contact_link = db.get_contact_link()
    return render_template('dashboard/settings.html', site_title=site_title, contact_link=contact_link)

@app.route('/dashboard/references', methods=['GET'])
def dashboard_references():
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    references = db.get_all_references()
    categories = db.get_reference_categories()
    folders = db.get_reference_folders()

    return render_template('dashboard/references.html', site_title=site_title,
                          references=references, categories=categories, folders=folders)

@app.route('/dashboard/references/add', methods=['GET', 'POST'])
def dashboard_add_reference():
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    categories = db.get_reference_categories()
    folders = db.get_reference_folders()

    if request.method == 'POST':
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        description = request.form.get('description')
        public = 1 if request.form.get('public') else 0
        watermark = 1 if request.form.get('watermark') else 0
        name = request.form.get('name')

        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)

        if file:
            filename = secure_filename(file.filename)
            # Add timestamp to filename to avoid duplicates
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file_path = os.path.join('static/uploads/references', filename)

            # Save the file
            file.save(file_path)

            # If name is not provided, use the original filename without timestamp
            if not name:
                name = filename.split('_', 1)[1] if '_' in filename else filename

            # Add watermark if requested
            if watermark:
                watermarked_path = os.path.join('static/uploads/references', f"watermarked_{filename}")
                # Get custom watermark text if provided
                watermark_text = request.form.get('watermark_text')
                if add_watermark(file_path, watermarked_path, watermark_text):
                    # Replace original with watermarked version
                    os.replace(watermarked_path, file_path)

            # Save to database
            db.add_reference(filename, name, category, subcategory, description, public, watermark)
            flash('Reference added successfully')
            return redirect(url_for('dashboard_references'))

    return render_template('dashboard/add_reference.html', site_title=site_title,
                          categories=categories, folders=folders)

@app.route('/dashboard/references/edit/<int:ref_id>', methods=['GET', 'POST'])
def dashboard_edit_reference(ref_id):
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    reference = db.get_reference_by_id(ref_id)

    if not reference:
        flash('Reference not found')
        return redirect(url_for('dashboard_references'))

    categories = db.get_reference_categories()
    folders = db.get_reference_folders()

    if request.method == 'POST':
        category = request.form.get('category')
        subcategory = request.form.get('subcategory')
        description = request.form.get('description')
        public = 1 if request.form.get('public') else 0
        name = request.form.get('name')

        # If name is not provided, use the filename without timestamp
        if not name and reference.filename:
            name = reference.filename.split('_', 1)[1] if '_' in reference.filename else reference.filename

        # Update reference
        db.update_reference(ref_id, name, category, subcategory, description, public)
        flash('Reference updated successfully')
        return redirect(url_for('dashboard_references'))

    return render_template('dashboard/edit_reference.html', site_title=site_title,
                          reference=reference, categories=categories, folders=folders)

@app.route('/dashboard/references/delete/<int:ref_id>', methods=['POST'])
def dashboard_delete_reference(ref_id):
    if not is_authenticated():
        return redirect(url_for('login'))

    # Delete reference and get filename
    filename = db.delete_reference(ref_id)

    if filename:
        file_path = os.path.join('static/uploads/references', filename)

        # Delete file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)

        flash('Reference deleted successfully')
    else:
        flash('Reference not found')

    return redirect(url_for('dashboard_references'))

@app.route('/dashboard/custom_references', methods=['GET'])
def dashboard_custom_references():
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    custom_refs = db.get_custom_references()

    return render_template('dashboard/custom_references.html', site_title=site_title,
                          custom_refs=custom_refs)

@app.route('/dashboard/custom_references/add', methods=['GET', 'POST'])
def dashboard_add_custom_reference():
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    references = db.get_all_references()

    if request.method == 'POST':
        name = request.form.get('name')
        selected_refs = request.form.getlist('references')

        if not name or not selected_refs:
            flash('Name and at least one reference are required')
            return redirect(request.url)

        # Generate unique link ID
        link_id = str(uuid.uuid4())[:8]

        # Create custom reference
        db.create_custom_reference(name, link_id, selected_refs)
        flash('Custom reference created successfully')
        return redirect(url_for('dashboard_custom_references'))

    return render_template('dashboard/add_custom_reference.html', site_title=site_title,
                          references=references)

@app.route('/dashboard/custom_references/edit/<int:custom_ref_id>', methods=['GET', 'POST'])
def dashboard_edit_custom_reference(custom_ref_id):
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    custom_ref = db.get_custom_reference_by_id(custom_ref_id)

    if not custom_ref:
        flash('Custom reference not found')
        return redirect(url_for('dashboard_custom_references'))

    all_references = db.get_all_references()
    selected_refs = db.get_selected_references_for_custom_ref(custom_ref_id)

    if request.method == 'POST':
        name = request.form.get('name')
        new_selected_refs = request.form.getlist('references')

        if not name or not new_selected_refs:
            flash('Name and at least one reference are required')
            return redirect(request.url)

        # Update custom reference
        db.update_custom_reference(custom_ref_id, name, new_selected_refs)
        flash('Custom reference updated successfully')
        return redirect(url_for('dashboard_custom_references'))

    return render_template('dashboard/edit_custom_reference.html', site_title=site_title,
                          custom_ref=custom_ref, all_references=all_references, 
                          selected_refs=selected_refs)

@app.route('/dashboard/custom_references/delete/<int:custom_ref_id>', methods=['POST'])
def dashboard_delete_custom_reference(custom_ref_id):
    if not is_authenticated():
        return redirect(url_for('login'))

    # Delete custom reference
    db.delete_custom_reference(custom_ref_id)
    flash('Custom reference deleted successfully')
    return redirect(url_for('dashboard_custom_references'))

@app.route('/dashboard/artists', methods=['GET'])
def dashboard_artists():
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    artists = db.get_all_artists()

    return render_template('dashboard/artists.html', site_title=site_title, artists=artists)

@app.route('/dashboard/artists/add', methods=['GET', 'POST'])
def dashboard_add_artist():
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()

    if request.method == 'POST':
        name = request.form.get('name')
        social_links = request.form.get('social_links')
        notes = request.form.get('notes')

        if not name:
            flash('Artist name is required')
            return redirect(request.url)

        # Add artist
        db.add_artist(name, social_links, notes)
        flash('Artist added successfully')
        return redirect(url_for('dashboard_artists'))

    return render_template('dashboard/add_artist.html', site_title=site_title)

@app.route('/dashboard/artists/edit/<int:artist_id>', methods=['GET', 'POST'])
def dashboard_edit_artist(artist_id):
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    artist = db.get_artist_by_id(artist_id)

    if not artist:
        flash('Artist not found')
        return redirect(url_for('dashboard_artists'))

    if request.method == 'POST':
        name = request.form.get('name')
        social_links = request.form.get('social_links')
        notes = request.form.get('notes')

        if not name:
            flash('Artist name is required')
            return redirect(request.url)

        # Update artist
        db.update_artist(artist_id, name, social_links, notes)
        flash('Artist updated successfully')
        return redirect(url_for('dashboard_artists'))

    return render_template('dashboard/edit_artist.html', site_title=site_title, artist=artist)

@app.route('/dashboard/artists/delete/<int:artist_id>', methods=['POST'])
def dashboard_delete_artist(artist_id):
    if not is_authenticated():
        return redirect(url_for('login'))

    # Delete artist
    if db.delete_artist(artist_id):
        flash('Artist deleted successfully')
    else:
        flash('Cannot delete artist with existing commissions')

    return redirect(url_for('dashboard_artists'))

@app.route('/dashboard/commissions', methods=['GET'])
def dashboard_commissions():
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    commissions = db.get_all_commissions()

    return render_template('dashboard/commissions.html', site_title=site_title, commissions=commissions)

@app.route('/dashboard/commissions/add', methods=['GET', 'POST'])
def dashboard_add_commission():
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    artists = db.get_all_artists()
    custom_refs = db.get_custom_references()

    if request.method == 'POST':
        title = request.form.get('title')
        artist_id = request.form.get('artist_id')
        description = request.form.get('description')
        price = request.form.get('price')
        commission_date = request.form.get('commission_date')
        commission_link = request.form.get('commission_link')
        custom_ref_id = request.form.get('custom_ref_id') or None
        public = 1 if request.form.get('public') else 0

        if not title or not artist_id:
            flash('Title and artist are required')
            return redirect(request.url)

        # Add commission
        commission_id = db.add_commission(title, artist_id, description, price, commission_date, 
                                         commission_link, custom_ref_id, public)

        # Handle image uploads
        if 'images' in request.files:
            images = request.files.getlist('images')
            watermark = 1 if request.form.get('watermark') else 0
            watermark_text = request.form.get('watermark_text')

            # Get image order from form if available
            image_order = request.form.get('image-order', '')
            ordered_indices = []

            if image_order:
                try:
                    # Convert comma-separated string to list of integers
                    ordered_indices = [int(idx) for idx in image_order.split(',')]
                except ValueError:
                    # If conversion fails, use default order
                    ordered_indices = list(range(len(images)))
            else:
                # If no order specified, use default order
                ordered_indices = list(range(len(images)))

            # Create commission folder structure
            commission_folder = os.path.join('static/uploads/commissions', str(commission_id))
            original_folder = os.path.join(commission_folder, 'original')
            watermarked_folder = os.path.join(commission_folder, 'watermarked')

            # Create directories if they don't exist
            os.makedirs(original_folder, exist_ok=True)
            os.makedirs(watermarked_folder, exist_ok=True)

            # Create a list to store image objects with their original indices
            image_list = []
            for i, image in enumerate(images):
                if image and image.filename:
                    image_list.append((i, image))

            # Process images in the order specified by ordered_indices
            for display_order, original_idx in enumerate(ordered_indices):
                # Find the image with the original index
                for idx, (i, image) in enumerate(image_list):
                    if i == original_idx:
                        # Original filename for storage
                        original_filename = secure_filename(image.filename)
                        # Add timestamp and index to avoid duplicates
                        original_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{display_order}_{original_filename}"
                        original_path = os.path.join(original_folder, original_filename)

                        # Save the original file
                        image.save(original_path)

                        # Database filename (path relative to static/uploads)
                        db_filename = original_filename
                        # Use forward slashes for URL paths
                        db_path = f"{str(commission_id)}/original/{original_filename}"

                        # Add watermark if requested
                        if watermark:
                            # Generate UUID for watermarked image
                            watermarked_filename = f"{uuid.uuid4()}.jpg"
                            watermarked_path = os.path.join(watermarked_folder, watermarked_filename)

                            if add_watermark(original_path, watermarked_path, watermark_text):
                                # Use watermarked image for display
                                db_filename = watermarked_filename
                                # Use forward slashes for URL paths
                                db_path = f"{str(commission_id)}/watermarked/{watermarked_filename}"

                        # Save to database with the appropriate path
                        db.add_commission_image(commission_id, db_path, display_order)

                        # Remove the processed image from the list
                        image_list.pop(idx)
                        break

        flash('Commission added successfully')
        return redirect(url_for('dashboard_commissions'))

    return render_template('dashboard/add_commission.html', site_title=site_title,
                          artists=artists, custom_refs=custom_refs)

@app.route('/dashboard/commissions/edit/<int:commission_id>', methods=['GET', 'POST'])
def dashboard_edit_commission(commission_id):
    if not is_authenticated():
        return redirect(url_for('login'))

    site_title = db.get_site_title()
    commission = db.get_commission_by_id(commission_id, public_only=False)

    if not commission:
        flash('Commission not found')
        return redirect(url_for('dashboard_commissions'))

    artists = db.get_all_artists()
    custom_refs = db.get_custom_references()
    images = commission['images']

    if request.method == 'POST':
        title = request.form.get('title')
        artist_id = request.form.get('artist_id')
        description = request.form.get('description')
        price = request.form.get('price')
        commission_date = request.form.get('commission_date')
        commission_link = request.form.get('commission_link')
        custom_ref_id = request.form.get('custom_ref_id') or None
        public = 1 if request.form.get('public') else 0

        if not title or not artist_id:
            flash('Title and artist are required')
            return redirect(request.url)

        # Update commission
        db.update_commission(commission_id, title, artist_id, description, price, commission_date, 
                           commission_link, custom_ref_id, public)

        # Process image order if provided
        image_order = request.form.get('image-order', '')
        if image_order:
            try:
                # Convert comma-separated string to list of image IDs
                ordered_image_ids = [int(img_id) for img_id in image_order.split(',')]

                # Create a list of tuples (image_id, display_order)
                image_orders = [(img_id, idx) for idx, img_id in enumerate(ordered_image_ids)]

                # Update the display_order of images in the database
                db.update_commission_image_order(image_orders)
            except ValueError as e:
                print(f"Error processing image order: {e}")

        # Handle image uploads
        if 'images' in request.files:
            images = request.files.getlist('images')
            watermark = 1 if request.form.get('watermark') else 0
            watermark_text = request.form.get('watermark_text')

            # Create commission folder structure
            commission_folder = os.path.join('static/uploads/commissions', str(commission_id))
            original_folder = os.path.join(commission_folder, 'original')
            watermarked_folder = os.path.join(commission_folder, 'watermarked')

            # Create directories if they don't exist
            os.makedirs(original_folder, exist_ok=True)
            os.makedirs(watermarked_folder, exist_ok=True)

            for i, image in enumerate(images):
                if image and image.filename:
                    # Original filename for storage
                    original_filename = secure_filename(image.filename)
                    # Add timestamp and index to avoid duplicates
                    original_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{i}_{original_filename}"
                    original_path = os.path.join(original_folder, original_filename)

                    # Save the original file
                    image.save(original_path)

                    # Database filename (path relative to static/uploads)
                    db_filename = original_filename
                    # Use forward slashes for URL paths
                    db_path = f"{str(commission_id)}/original/{original_filename}"

                    # Add watermark if requested
                    if watermark:
                        # Generate UUID for watermarked image
                        watermarked_filename = f"{uuid.uuid4()}.jpg"
                        watermarked_path = os.path.join(watermarked_folder, watermarked_filename)

                        if add_watermark(original_path, watermarked_path, watermark_text):
                            # Use watermarked image for display
                            db_filename = watermarked_filename
                            # Use forward slashes for URL paths
                            db_path = f"{str(commission_id)}/watermarked/{watermarked_filename}"

                    # Save to database with the appropriate path
                    db.add_commission_image(commission_id, db_path, i + len(commission['images']))

        flash('Commission updated successfully')
        return redirect(url_for('dashboard_commissions'))

    return render_template('dashboard/edit_commission.html', site_title=site_title,
                          commission=commission, artists=artists, 
                          custom_refs=custom_refs, images=images)

@app.route('/dashboard/commissions/delete/<int:commission_id>', methods=['POST'])
def dashboard_delete_commission(commission_id):
    if not is_authenticated():
        return redirect(url_for('login'))

    # Delete commission from database
    db.delete_commission(commission_id)

    # Delete the entire commission folder
    commission_folder = os.path.join('static/uploads/commissions', str(commission_id))
    if os.path.exists(commission_folder) and os.path.isdir(commission_folder):
        # Delete all files in the original subfolder
        original_folder = os.path.join(commission_folder, 'original')
        if os.path.exists(original_folder):
            for file in os.listdir(original_folder):
                file_path = os.path.join(original_folder, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(original_folder)

        # Delete all files in the watermarked subfolder
        watermarked_folder = os.path.join(commission_folder, 'watermarked')
        if os.path.exists(watermarked_folder):
            for file in os.listdir(watermarked_folder):
                file_path = os.path.join(watermarked_folder, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            os.rmdir(watermarked_folder)

        # Remove the commission folder itself
        os.rmdir(commission_folder)

    flash('Commission deleted successfully')
    return redirect(url_for('dashboard_commissions'))

@app.route('/dashboard/commissions/delete_image/<int:image_id>', methods=['POST'])
def dashboard_delete_commission_image(image_id):
    if not is_authenticated():
        return redirect(url_for('login'))

    # Delete image and get details
    result = db.delete_commission_image(image_id)

    if result:
        commission_id = result['commission_id']
        filename = result['filename']

        # Construct the full path to the file
        file_path = os.path.join('static/uploads/commissions', filename)

        # Delete file if it exists
        if os.path.exists(file_path):
            os.remove(file_path)

        # Check if this is a watermarked image and delete the original too if needed
        if 'watermarked' in filename:
            # Get the original filename by replacing 'watermarked' with 'original'
            # This is a simplistic approach - in a real system you might want to store
            # the relationship between original and watermarked files in the database
            parts = filename.split('/')
            if len(parts) >= 3 and parts[1] == 'watermarked':
                # The original should be in the same commission folder but in 'original' subfolder
                # We don't know the original filename, so we can't delete it directly
                # In a real system, you would store this relationship in the database
                pass

        flash('Image deleted successfully')
    else:
        flash('Image not found')
        return redirect(url_for('dashboard_commissions'))

    return redirect(url_for('dashboard_edit_commission', commission_id=commission_id))

# Download commission folder as zip
@app.route('/download_commission_folder/<int:commission_id>', methods=['GET'])
def download_commission_folder(commission_id):
    if not is_authenticated():
        return redirect(url_for('login'))

    # Get commission details
    commission = db.get_commission_by_id(commission_id, public_only=False)

    if not commission:
        flash('Commission not found')
        return redirect(url_for('commissions'))

    # Create in-memory zip file
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        # Path to commission folder
        commission_folder = os.path.join('static/uploads/commissions', str(commission_id))

        # Add original files
        original_folder = os.path.join(commission_folder, 'original')
        if os.path.exists(original_folder):
            for file in os.listdir(original_folder):
                file_path = os.path.join(original_folder, file)
                if os.path.isfile(file_path):
                    # Add file to zip with path inside zip
                    zf.write(file_path, os.path.join('original', file))

        # Add watermarked files
        watermarked_folder = os.path.join(commission_folder, 'watermarked')
        if os.path.exists(watermarked_folder):
            for file in os.listdir(watermarked_folder):
                file_path = os.path.join(watermarked_folder, file)
                if os.path.isfile(file_path):
                    # Add file to zip with path inside zip
                    zf.write(file_path, os.path.join('watermarked', file))

    # Reset file pointer
    memory_file.seek(0)

    # Create zip filename
    zip_filename = f"{commission['title']} - Commission Files.zip"

    return Response(
        memory_file.getvalue(),
        mimetype='application/zip',
        headers={'Content-Disposition': f'attachment; filename="{zip_filename}"'}
    )

# Download references as zip
@app.route('/download_references_zip', methods=['GET', 'POST'])
def download_references_zip():
    if request.method == 'POST':
        reference_ids = request.json.get('reference_ids', [])
        custom_ref_name = request.json.get('custom_ref_name', None)

        # If no reference IDs provided, return error
        if not reference_ids:
            return jsonify({'error': 'No references selected'}), 400

        # If only one reference, redirect to direct download
        if len(reference_ids) == 1:
            ref = db.get_reference_by_id(reference_ids[0])
            if ref:
                return jsonify({
                    'single_file': True,
                    'download_url': url_for('static', filename=f'uploads/references/{ref["filename"]}')
                })

        # Store reference IDs and custom ref name in session for GET request
        session['download_reference_ids'] = reference_ids
        session['download_custom_ref_name'] = custom_ref_name

        # Return success response
        return jsonify({'success': True})

    else:  # GET request
        # Get reference IDs and custom ref name from session
        reference_ids = session.get('download_reference_ids', [])
        custom_ref_name = session.get('download_custom_ref_name', None)

        # Clear session data
        session.pop('download_reference_ids', None)
        session.pop('download_custom_ref_name', None)

        # If no reference IDs provided, return error
        if not reference_ids:
            flash('No references selected for download')
            return redirect(url_for('references'))

        # Get references from database
        references = []
        for ref_id in reference_ids:
            ref = db.get_reference_by_id(ref_id)
            if ref:
                references.append(ref)

        if not references:
            flash('No valid references found')
            return redirect(url_for('references'))

        # Create in-memory zip file
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Organize references by category and subcategory
            for ref in references:
                category = ref['category']
                subcategory = ref['subcategory']
                filename = ref['filename']

                # Create path within zip file
                zip_path = f"{category}/{subcategory}/{filename}"

                # Get file path on disk
                file_path = os.path.join('static/uploads/references', filename)

                # Add file to zip if it exists
                if os.path.exists(file_path):
                    zf.write(file_path, zip_path)

        # Reset file pointer
        memory_file.seek(0)

        # Get site title for zip filename
        site_title = db.get_site_title()

        # Create zip filename
        if custom_ref_name:
            zip_filename = f"{site_title} References - {custom_ref_name}.zip"
        else:
            current_date = datetime.now().strftime('%Y-%m-%d')
            zip_filename = f"{site_title} References - {current_date}.zip"

        return Response(
            memory_file.getvalue(),
            mimetype='application/zip',
            headers={
                'Content-Disposition': f'attachment; filename="{zip_filename}"'
            }
        )

# This app object is used by Gunicorn. To run with Gunicorn:
# gunicorn -c gunicorn_config.py app:app

# Run the app directly (development only)
if __name__ == '__main__':
    import sys
    import ssl

    # Default configuration
    host = '127.0.0.1'
    port = 8000
    use_ssl = False

    # Check command line arguments for port selection
    if len(sys.argv) > 1 and sys.argv[1] == '--https':
        port = 443
        use_ssl = True

    if use_ssl:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        try:
            # You would need to create/obtain these certificate files
            context.load_cert_chain('cert.pem', 'key.pem')
            app.run(host=host, port=port, ssl_context=context, debug=True)
        except (FileNotFoundError, ssl.SSLError):
            print("Error: SSL certificates not found or invalid.")
            print("To use HTTPS (port 443), you need valid SSL certificates.")
            print("For development, you can generate self-signed certificates with:")
            print("  openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365")
            print("\nFalling back to HTTP on port 8000...")
            app.run(host=host, port=8000, debug=True)
    else:
        # HTTP on port 8000
        app.run(host=host, port=port, debug=True)
