from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_migrate import Migrate
from flask_mail import Mail, Message
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from config import config

# Import our db instance instead of creating a new one
from models import db
from models.user import User
from models.analytics import PageVisit
from models.project import Project
from models.testimonial import Testimonial, Badge

# Initialize login manager
login_manager = LoginManager()
login_manager.login_view = 'admin_login'

# Initialize Mail
mail = Mail()

def create_app(config_name='default'):
    # Initialize Flask app
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.config['MAIL_DEBUG'] = True  
    import logging
    logging.basicConfig(level=logging.DEBUG)

    # Initialize extensions with app
    migrate = Migrate(app, db)
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # Add context processor to make 'now' available in all templates
    @app.context_processor
    def inject_now():
        return {
            'now': datetime.now(),
            'min': min}

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Helper functions
    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    def track_visit(page):
        visit = PageVisit(
            page=page,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string
        )
        db.session.add(visit)
        db.session.commit()

    # Public routes
    @app.route('/')
    def index():
        track_visit('home')
        projects = Project.query.order_by(Project.created_at.desc()).limit(3).all()
        testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
        badges = Badge.query.order_by(Badge.earned_date.desc()).all()
        return render_template('public/index.html', projects=projects, testimonials=testimonials, badges=badges)

    @app.route('/projects')
    def projects():
        track_visit('projects')
        projects = Project.query.order_by(Project.created_at.desc()).all()
        return render_template('public/projects.html', projects=projects)

    @app.route('/contact', methods=['GET', 'POST'])
    def contact():
        track_visit('contact')
        if request.method == 'POST':
            # Handle form data
            name = request.form.get('name')
            email = request.form.get('email')
            subject = request.form.get('subject')
            message = request.form.get('message')

            # Validate required fields
            if not all([name, email, subject, message]):
                flash('All fields are required', 'error')
                return redirect(url_for('contact'))

            # Create email message
            msg = Message(
                subject=f"New Contact Form Submission: {subject}",
                recipients=[app.config['MAIL_USERNAME']],
                body=f"""
                New message from your website:
                
                Name: {name}
                Email: {email}
                Subject: {subject}
                Message: {message}
                """
            )

            try:
                mail.send(msg)
                flash('Message sent successfully!', 'success')
            except Exception as e:
                app.logger.error(f"Email error: {str(e)}")
                flash('Error sending message. Please try again later.', 'error')

            return redirect(url_for('contact'))

        return render_template('public/contact.html')

    # Admin routes
    @app.route('/admin/login', methods=['GET', 'POST']) 
    def admin_login():
        if current_user.is_authenticated:
            return redirect(url_for('admin_dashboard'))
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('admin_dashboard'))
            else:
                flash('Invalid username or password')
        
        return render_template('admin/login.html')

    @app.route('/admin/logout')
    @login_required
    def admin_logout():
        logout_user()
        return redirect(url_for('index'))

    @app.route('/admin')
    @login_required
    def admin_dashboard():
        total_visits = PageVisit.query.count()
        page_stats = db.session.query(
            PageVisit.page, 
            db.func.count(PageVisit.id)
        ).group_by(PageVisit.page).all()
        
        projects = Project.query.order_by(Project.updated_at.desc()).limit(5).all()
        testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).limit(5).all()
        
        return render_template('admin/dashboard.html', 
                            total_visits=total_visits,
                            page_stats=page_stats,
                            projects=projects,
                            testimonials=testimonials)

    # Admin - Projects CRUD
    @app.route('/admin/projects')
    @login_required
    def admin_projects():
        projects = Project.query.order_by(Project.created_at.desc()).all()
        return render_template('admin/projects.html', projects=projects)

    @app.route('/admin/projects/add', methods=['GET', 'POST'])
    @login_required
    def add_project():
        if request.method == 'POST':
            title = request.form.get('title')
            description = request.form.get('description')
            location = request.form.get('location')
            
            client = request.form.get('client')
            category = request.form.get('category')
            technologies = request.form.get('technologies')
            challenges = request.form.get('challenges')
            solution = request.form.get('solution')
            repository = request.form.get('repository')
            
            start_date = None
            end_date = None
            if request.form.get('start_date'):
                start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            if request.form.get('end_date'):
                end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            
            project = Project(
                title=title,
                description=description,
                location=location,
                start_date=start_date,
                end_date=end_date,
                client=client,
                category=category,
                technologies=technologies,
                challenges=challenges,
                solution=solution,
                repository=repository
            )
            
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    project.image = os.path.join('uploads', filename).replace('\\', '/')
            
            db.session.add(project)
            db.session.commit()
            flash('Project added successfully')
            return redirect(url_for('admin_projects'))
        
        return render_template('admin/edit_project.html')

    @app.route('/admin/projects/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_project(id):
        project = Project.query.get_or_404(id)
        
        if request.method == 'POST':
            project.title = request.form.get('title')
            project.description = request.form.get('description')
            project.location = request.form.get('location')
            
            project.client = request.form.get('client')
            project.category = request.form.get('category')
            project.technologies = request.form.get('technologies')
            project.challenges = request.form.get('challenges')
            project.solution = request.form.get('solution')
            project.repository = request.form.get('repository')
            
            if request.form.get('start_date'):
                project.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
            if request.form.get('end_date'):
                project.end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()
            
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    project.image = os.path.join('uploads', filename).replace('\\', '/')
            
            db.session.commit()
            flash('Project updated successfully')
            return redirect(url_for('admin_projects'))
        
        return render_template('admin/edit_project.html', project=project)

    @app.route('/admin/projects/delete/<int:id>')
    @login_required
    def delete_project(id):
        project = Project.query.get_or_404(id)
        db.session.delete(project)
        db.session.commit()
        flash('Project deleted successfully')
        return redirect(url_for('admin_projects'))

    # Admin - Testimonials CRUD
    @app.route('/admin/testimonials')
    @login_required
    def admin_testimonials():
        testimonials = Testimonial.query.order_by(Testimonial.created_at.desc()).all()
        return render_template('admin/testimonial.html', testimonials=testimonials)

    @app.route('/admin/testimonials/add', methods=['GET', 'POST'])
    @login_required
    def add_testimonial():
        if request.method == 'POST':
            name = request.form.get('name')
            position = request.form.get('position')
            content = request.form.get('content')
            
            testimonial = Testimonial(
                name=name,
                position=position,
                content=content
            )
            
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    testimonial.image = os.path.join('uploads', filename)
            
            db.session.add(testimonial)
            db.session.commit()
            flash('Testimonial added successfully')
            return redirect(url_for('admin_testimonials'))
        
        return render_template('admin/edit_testimonial.html')

    @app.route('/admin/testimonials/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_testimonial(id):
        testimonial = Testimonial.query.get_or_404(id)
        
        if request.method == 'POST':
            testimonial.name = request.form.get('name')
            testimonial.position = request.form.get('position')
            testimonial.content = request.form.get('content')
            
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    testimonial.image = os.path.join('uploads', filename)
            
            db.session.commit()
            flash('Testimonial updated successfully')
            return redirect(url_for('admin_testimonials'))
        
        return render_template('admin/edit_testimonial.html', testimonial=testimonial)

    @app.route('/admin/testimonials/delete/<int:id>')
    @login_required
    def delete_testimonial(id):
        testimonial = Testimonial.query.get_or_404(id)
        db.session.delete(testimonial)
        db.session.commit()
        flash('Testimonial deleted successfully')
        return redirect(url_for('admin_testimonials'))

    # Admin - Badges CRUD
    @app.route('/admin/badges')
    @login_required
    def admin_badges():
        badges = Badge.query.order_by(Badge.earned_date.desc()).all()
        return render_template('admin/badges.html', badges=badges)

    @app.route('/admin/badges/add', methods=['GET', 'POST'])
    @login_required
    def add_badge():
        if request.method == 'POST':
            title = request.form.get('title')
            issuer = request.form.get('issuer')
            url = request.form.get('url')
            
            earned_date = None
            if request.form.get('earned_date'):
                earned_date = datetime.strptime(request.form.get('earned_date'), '%Y-%m-%d').date()
            
            badge = Badge(
                title=title,
                issuer=issuer,
                url=url,
                earned_date=earned_date
            )
            
            if 'image' in request.files:
                file = request.files['image']
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    badge.image = os.path.join('uploads', filename).replace('\\', '/')
            
            db.session.add(badge)
            db.session.commit()
            flash('Badge added successfully')
            return redirect(url_for('admin_badges'))
        
        return render_template('admin/edit_badge.html')

    @app.route('/admin/badges/edit/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_badge(id):
        badge = Badge.query.get_or_404(id)
        
        if request.method == 'POST':
            badge.title = request.form.get('title')
            badge.issuer = request.form.get('issuer')
            badge.url = request.form.get('url')
            
            if request.form.get('earned_date'):
                badge.earned_date = datetime.strptime(request.form.get('earned_date'), '%Y-%m-%d').date()
            
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    badge.image = os.path.join('uploads', filename).replace('\\', '/')
            
            db.session.commit()
            flash('Badge updated successfully')
            return redirect(url_for('admin_badges'))
        
        return render_template('admin/edit_badge.html', badge=badge)

    @app.route('/admin/badges/delete/<int:id>')
    @login_required
    def delete_badge(id):
        badge = Badge.query.get_or_404(id)
        db.session.delete(badge)
        db.session.commit()
        flash('Badge deleted successfully')
        return redirect(url_for('admin_badges'))

    # Command to initialize the database
    @app.cli.command('init-db')
    def init_db_command():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app('development')
    with app.app_context():
        db.create_all()
    # Use the PORT environment variable for Cloud Run
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port)