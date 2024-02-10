

import datetime
import dateutil.tz
import flask_login
import pathlib
from flask_login import current_user
from flask import Blueprint, render_template, request, redirect, url_for, abort, current_app, flash
from . import db, bcrypt
from sqlalchemy import func, or_
from flask import jsonify
from sqlalchemy.orm import aliased
from . import model

bp = Blueprint("main", __name__)


# INDEX CONTROLLER

@bp.route("/")
def index():
    # get the page number
    page = request.args.get('page', 1, type=int)

    # number of recipes we want to have per page
    per_page = 9

    rating_alias = aliased(model.Rating)

    # create the query to retrieve all the recipes from the database
    query = (
        db.select(model.Recipe)
        .join(model.User)
        .outerjoin(rating_alias, model.Recipe.id == rating_alias.recipe_id)
        .group_by(model.Recipe.id)
        .order_by(func.coalesce(func.avg(rating_alias.value), 0).desc())
    )

    # define the offset to know that every 9 recipes a new page must appear
    offset = (page - 1) * per_page

    # apply the offset to get the correct subset of recipes and also specify the number of recipes you want to display in each page (12)
    recipes = db.session.execute(query.offset(offset).limit(per_page)).scalars().all()

    # check whether there is a previous or next page, that is if there are more recipes to display or not
    next_url = url_for('main.index', page=page + 1) if len(recipes) == per_page else None
    prev_url = url_for('main.index', page=page - 1) if page > 1 else None

    # compute the average ratings and total number of ratings for each recipe
    average_ratings = {}
    number_ratings = {}
    for recipe in recipes:
        ratings = model.Rating.query.filter_by(recipe_id=recipe.id).all()
        average_rating = sum(r.value for r in ratings) / len(ratings) if ratings else 0
        average_ratings[recipe.id] = round(average_rating, 2)
        number_ratings[recipe.id] = len(ratings)
    return render_template('main/index.html', average_ratings=average_ratings, number_ratings=number_ratings, recipes=recipes, next_url=next_url, prev_url=prev_url)


# ABOUT US TEMPLATE CONTROLLER

@bp.route("/aboutUs")
def about():
    return render_template("main/about.html")


# RECIPE VIEW CONTROLLER

@bp.route("/recipe/<int:recipe_id>")
def recipe_view(recipe_id):
    r = db.get_or_404(model.Recipe, recipe_id)
    # obtain the recipe that is being requested by the user
    query = db.select(model.Recipe).join(model.User)
    recipes = db.session.execute(query).scalars().all()
    # compute the average ratings for the recipes
    average_ratings = {}
    number_ratings = {}
    for recipe in recipes:
        ratings = model.Rating.query.filter_by(recipe_id=recipe.id).all()
        average_rating = sum(r.value for r in ratings) / len(ratings) if ratings else 0
        average_ratings[recipe.id] = round(average_rating,2)
        number_ratings[recipe.id] = len(ratings)
    return render_template("main/recipe.html", recipe=r, average_ratings=average_ratings, number_ratings=number_ratings)


# USER VIEW CONTROLLER

@bp.route("/user/<int:user_id>")
def user_view(user_id):
    user = db.get_or_404(model.User, user_id)
    # obtain the user that is being requested 
    query = db.select(model.Recipe).where(model.Recipe.user == user)
    recipes = db.session.execute(query).scalars().all()
    # compute the average ratings for the recipes
    average_ratings = {}
    number_ratings = {}
    for recipe in recipes:
        ratings = model.Rating.query.filter_by(recipe_id=recipe.id).all()
        average_rating = sum(r.value for r in ratings) / len(ratings) if ratings else 0
        average_ratings[recipe.id] = round(average_rating,2)
        number_ratings[recipe.id] = len(ratings)
    return render_template("main/user.html", user=user, recipes=recipes, average_ratings = average_ratings, number_ratings=number_ratings)


# CREATE/ADD A RECIPE TO THE DATABASE CONTROLLERS

@bp.route("/creation")
@flask_login.login_required
def create_recipe_view():
    return render_template("main/recipe_creation.html")

@bp.route("/creation",  methods=["POST"])
@flask_login.login_required
def create_recipe():
    # get the initial values from the form filled by the user
    title = request.form.get("title")
    
    try:
        number_persons = int(request.form.get("people"))
    except ValueError as e:
        flash(f'The number of servings must be an integer')
        return redirect(url_for("main.create_recipe"))

    try:
        cooking_time = int(request.form.get("time"))
    except ValueError as e:
        flash(f'The cooking time must be an integer')
        return redirect(url_for("main.create_recipe"))

    description = request.form.get("description")
    
    time_unit = request.form.get("unit")
    user = flask_login.current_user
    # update the database with those values
    recipe = model.Recipe(title=title, number_persons=number_persons, description=description, cooking_time=cooking_time, time_unit=time_unit, user=user)
    db.session.add(recipe)
    db.session.commit()
    return redirect(url_for("main.create_ingredients_steps_view", recipe_id=recipe.id))

@bp.route("/ingredientssteps/<int:recipe_id>")
@flask_login.login_required
def create_ingredients_steps_view(recipe_id):
    recipe = db.get_or_404(model.Recipe, recipe_id)
    # obtain the ingredients of the given recipe
    query = db.select(model.Ingredient)
    ingredients = db.session.execute(query).scalars().all()
    # check that the authenticated user is the one trying to modify the ingredients
    if current_user.id == recipe.user.id:
        return render_template("main/ingredients_steps.html", recipe=recipe, ingredients=ingredients)
    else:
        return redirect(url_for("main.index"))
   
@bp.route("/ingredientssteps/<int:recipe_id>", methods=["POST"])
@flask_login.login_required
def add_ingredient(recipe_id):
    # obtain all the ingredients, its units, and quantity
    recipe = db.get_or_404(model.Recipe, recipe_id)
    i = request.form.get("ingredient")
    
    try:
        quantity_str = request.form.get("quantity")
        q = int(quantity_str) 
    except ValueError as e:
        flash(f'The quantity must be an integer')
        return redirect(url_for("main.add_ingredient", recipe_id=recipe.id))
    u = request.form.get("unit")
    query = db.select(model.Ingredient).where(model.Ingredient.name == i)
    ingredient = db.session.execute(query).scalar_one_or_none()
    # add the ingredient to the database if it does not already exist
    if not ingredient:
        ingredient = model.Ingredient(name=i)
        db.session.add(ingredient)
        db.session.commit()
    q_ingredient = model.QuantifiedIngredient(quantity=q, ingredient_id=ingredient.id, units=u, recipe_id=recipe.id)
    db.session.add(q_ingredient)
    db.session.commit()
    return redirect(url_for("main.create_ingredients_steps_view", recipe_id=recipe.id))

@bp.route("/steps/<int:recipe_id>", methods=["POST"])
@flask_login.login_required
def add_step(recipe_id):
    # obtain all the steps and its positions
    recipe = db.get_or_404(model.Recipe, recipe_id)
    text = request.form.get("text")
    position = request.form.get("position")
   
    # add the given step to the database
    step = model.Step(position=position, text=text, recipe_id=recipe.id)
    db.session.add(step)
    db.session.commit()
    return redirect(url_for("main.create_ingredients_steps_view", recipe_id=recipe.id))

@bp.route("/done/<int:recipe_id>")
@flask_login.login_required
def recipe_done(recipe_id):
    # this function stores the new created recipe
    r = db.get_or_404(model.Recipe, recipe_id)
    query = db.select(model.Recipe).join(model.User).limit(10)
    recipes = db.session.execute(query).scalars().all()
    average_ratings = {}
    number_ratings = {}
    for recipe in recipes:
        ratings = model.Rating.query.filter_by(recipe_id=recipe.id).all()
        average_rating = sum(r.value for r in ratings) / len(ratings) if ratings else 0
        average_ratings[recipe.id] = round(average_rating,2)
        number_ratings[recipe.id] = len(ratings)
    return render_template("main/recipe.html", recipe=r, average_ratings=average_ratings, number_ratings=number_ratings)


# UPLOAD/ADD PHOTOS CONTROLLERS

# this function is for the user to be able to upload a photo when they are adding a recipe 
@bp.route("/photos-upload/<int:recipe_id>", methods=["POST"])
@flask_login.login_required
def photos_create_recipe(recipe_id):
    uploaded_file = request.files['photo']
    if uploaded_file.filename != '':
        content_type = uploaded_file.content_type
        if content_type == "image/png":
            file_extension = "png"
        elif content_type == "image/jpeg":
            file_extension = "jpg"
        else:
            abort(400, f"Unsupported file type {content_type}")
        recipe = db.get_or_404(model.Recipe, recipe_id)
        photo = model.Photo(
            user=flask_login.current_user,
            recipe=recipe,
            file_extension=file_extension)
        db.session.add(photo)
        db.session.commit()
    else:
        flash("The filename is empty!")
    path = (
    pathlib.Path(current_app.root_path)
    / "static"
    / "photos"
    / f"photo-{photo.id}.{file_extension}"
    )
    uploaded_file.save(path)
    # the user will be redirected to the template where the creation of recipes is taking place
    return redirect(url_for("main.create_ingredients_steps_view", recipe_id=recipe.id))

# this function is for the users to be able to upload a photo to an already existing recipe
@bp.route("/photos/<int:recipe_id>", methods=["POST"])
@flask_login.login_required
def photos(recipe_id):
    uploaded_file = request.files['photo']
    recipe = db.get_or_404(model.Recipe, recipe_id)
    content_type = uploaded_file.content_type
    content_type = uploaded_file.content_type
    if content_type == "image/png":
        file_extension = "png"
    elif content_type == "image/jpeg":
        file_extension = "jpg"
    else:
        abort(400, f"Unsupported file type {content_type}")
    photo = model.Photo(
        user=current_user,
        recipe=recipe,
        file_extension=file_extension
    )
    db.session.add(photo)
    db.session.commit()
    path = pathlib.Path(current_app.root_path) / "static" / "photos" / f"photo-{photo.id}.{file_extension}"
    uploaded_file.save(path)
    # the user will be redirected to the template that shows the recipe to which he/she is adding an image
    return redirect(url_for("main.recipe_view", recipe_id=recipe.id))

# this function allows the user to upload a profile image to its profile
@bp.route("/upload-profile-image", methods=['POST'])
@flask_login.login_required
def upload_profile_image():
    uploaded_file = request.files['profile_photo']
    content_type = uploaded_file.content_type
    content_type = uploaded_file.content_type
    if content_type == "image/png":
        file_extension = "png"
    elif content_type == "image/jpeg":
        file_extension = "jpg"
    else:
        abort(400, f"Unsupported file type {content_type}")
    profile_photo = model.ProfilePhoto(
        user=current_user,
        file_extension=file_extension
    )
    db.session.add(profile_photo)
    db.session.commit()
    # this updates the user profile photo
    current_user.profile_photos.append(profile_photo)
    db.session.commit()
    path = pathlib.Path(current_app.root_path) / "static" / "profile_photos" / f"photo-{profile_photo.id}.{file_extension}"
    uploaded_file.save(path)
    # the user will be redirected to the template of its own profile and will see the changes on it (the new profile image will be uploaded)
    return redirect(url_for('main.user_view', user_id=current_user.id))

# this function allows the user to upload a background image to its profile
@bp.route("/upload-background-image", methods=['POST'])
@flask_login.login_required
def upload_background_image():
    uploaded_file = request.files['background_photo']
    content_type = uploaded_file.content_type
    content_type = uploaded_file.content_type
    if content_type == "image/png":
        file_extension = "png"
    elif content_type == "image/jpeg":
        file_extension = "jpg"
    else:
        abort(400, f"Unsupported file type {content_type}")
    background_photo = model.BackgroundPhoto(
        user=current_user,
        file_extension=file_extension
    )
    db.session.add(background_photo)
    db.session.commit()
    # this updates the user background photo
    current_user.background_photos.append(background_photo)
    db.session.commit()
    path = pathlib.Path(current_app.root_path) / "static" / "background_photos" / f"photo-{background_photo.id}.{file_extension}"
    uploaded_file.save(path)
    # the user will be redirected to the template of its own profile and will see the changes on it (the new background image will be uploaded)
    return redirect(url_for('main.user_view', user_id=current_user.id))


# BOOKMARKS CONTROLLERS

@bp.route("/bookmarks")
@flask_login.login_required
def bookmarks():
    # make sure that the user that is trying to bookmark a recipe is authenticated
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login')) # else, redirect to the login template
    user = current_user
    recipes = [bookmark.recipe for bookmark in user.bookmarks]
    average_ratings = {}
    number_ratings = {}
    for recipe in recipes:
        ratings = model.Rating.query.filter_by(recipe_id=recipe.id).all()
        average_rating = sum(r.value for r in ratings) / len(ratings) if ratings else 0
        average_ratings[recipe.id] = round(average_rating,2)
        number_ratings[recipe.id] = len(ratings)
    return render_template("main/bookmarks.html", user=user, average_ratings = average_ratings, number_ratings=number_ratings)

# this function adds a route to display the bookmarks of a specific user
@bp.route("/bookmarks/<int:recipe_id>", methods=["POST"])
@flask_login.login_required
def bookmarks_view(recipe_id):
    recipe = db.get_or_404(model.Recipe, recipe_id)
    user = current_user
    # check is the user has already bookmarked the given recipe
    existing_bookmark = model.Bookmark.query.filter_by(user_id=user.id, recipe_id=recipe.id).first()
    # if not, then the bookmark will be added to the database
    if existing_bookmark is None:
        bookmark = model.Bookmark(user=user, recipe=recipe)
        db.session.add(bookmark)
        db.session.commit()
    # else, the bookmark of the recipe by the specific user will be deleted from the database
    else:
        db.session.delete(existing_bookmark)
        db.session.commit()

    # Use referrer to redirect back to the same page
    redirect_destination = request.referrer or url_for("main.index")

    return redirect(redirect_destination)

# this function allows to get the bookmark status of the recipe given by a specific user 
@bp.route('/get_bookmark_status/<int:user_id>/<int:recipe_id>', methods=['GET'])
def get_bookmark_status(user_id, recipe_id):
    # check that the current user is authenticated
    if current_user.is_authenticated:
        # check if they have bookmarked the recipe
        bookmarked = model.Bookmark.query.filter_by(user_id=user_id, recipe_id=recipe_id).first() is not None
        # return that the recipe bookmark belongs to the class 'bookmarked'
        return jsonify({'bookmarked': bookmarked})
    else:
        # if the user has not bookmarked the recipe, make the value equal to None
        bookmarked = None
        return jsonify({'bookmarked': bookmarked})


# RATINGS CONTROLLERS 

@bp.route("/rate/<int:recipe_id>", methods=["POST"])
@flask_login.login_required
def rate_recipe(recipe_id):
    recipe = db.get_or_404(model.Recipe, recipe_id)
    user = current_user
    rating_value = request.form.get("rating")
    # check if the authenticated user has already rated the recipe
    existing_rating = model.Rating.query.filter_by(user_id=user.id, recipe_id=recipe.id).first()
    # if they have not rated the recipe, the value they give will be stored in the database
    if existing_rating is None:
        new_rating = model.Rating(value=rating_value, user=user, recipe=recipe)
        db.session.add(new_rating)
        db.session.commit()
    # else, the value will be updated in the database
    else:
        existing_rating.value = rating_value
        db.session.commit()
    #average_rating = db.session.query(func.avg(model.Rating.value).label('average')).filter_by(recipe_id=recipe.id).scalar()
    #recipe.average_rating = average_rating
    #db.session.commit()
    # Determine the redirect destination based on the referer header (to the index or to the recipe again)
    redirect_destination = request.referrer or url_for("main.index")
    
    return redirect(redirect_destination)

# this function allows to get the rating that was given to a recipe by a specific user
@bp.route('/get_user_rating/<int:user_id>/<int:recipe_id>', methods=['GET'])
def get_user_rating(user_id, recipe_id):
    # obtain the rating and return its value
    user_rating = model.Rating.query.filter_by(user_id=user_id, recipe_id=recipe_id).first()
    return jsonify({'userRating': user_rating.value if user_rating else None})


# SEARCH FILTER CONTROLLERS

@bp.route("/search")
def search():
    results=[]
    return render_template('main/results.html', results=results)

@bp.route("/search/results", methods=['GET'])
def new_search():
    q = request.args.get('q')
    if q:
        # convert all the terms to lower case
        q_lower = q.lower()

        # create a query that will select those recipes according to what the user puts as input. The recipes will be displayed according to if the given
        # word appeard in the title, ingredients, steps, or description of the recipe (in that specific order)
        query = (
            db.select(model.Recipe)
            .join(model.QuantifiedIngredient, isouter=True)
            .join(model.Ingredient, isouter=True)
            .join(model.Step, isouter=True)
            .where(
                or_(
                    func.lower(model.Recipe.title).ilike(f"%{q_lower}%"),
                    func.lower(model.Ingredient.name).ilike(f"%{q_lower}%"),
                    func.lower(model.Step.text).ilike(f"%{q_lower}%"),
                    func.lower(model.Recipe.description).ilike(f"%{q_lower}%")
                    
                )
            )
            .order_by(
                func.lower(model.Recipe.title).ilike(f"%{q_lower}%").desc(),
                func.lower(model.Ingredient.name).ilike(f"%{q_lower}%"),
                func.lower(model.Step.text).ilike(f"%{q_lower}%"),
                func.lower(model.Recipe.description).ilike(f"%{q_lower}%").desc()
            )
            .distinct()
        )
        results = db.session.execute(query).scalars().all()
        print(results)
    else:
        results = []
    recipes = db.session.execute(query).scalars().all()
    average_ratings = {}
    for recipe in recipes:
        ratings = model.Rating.query.filter_by(recipe_id=recipe.id).all()
        average_rating = sum(r.value for r in ratings) / len(ratings) if ratings else 0
        average_ratings[recipe.id] = round(average_rating,2)
    return render_template('main/search_results.html', results=results, average_ratings=average_ratings)


# VIEW USER RATED RECIPES TEMPLATE CONTROLLER

@bp.route('/rated_recipes', methods=['GET'])
@flask_login.login_required
def view_user_rated_recipes():
    user = current_user
    # Subquery to filter recipes based on the current user's ratings
    subquery = (
        db.select(model.Rating.recipe_id)
        .where(model.Rating.user_id == current_user.id)
        .distinct()
    ).alias("user_ratings")

    # Query to select recipes that have been rated by the current user. This way to avoid errors!
    query = (
        db.select(model.Recipe)
        .join(model.User)
        .join(subquery, model.Recipe.id == subquery.c.recipe_id)
    )

    rated_recipes = db.session.execute(query).scalars().all()

    # Calculate average ratings for the selected recipes
    average_ratings = {}
    number_ratings = {}
    for recipe in rated_recipes:
        ratings = model.Rating.query.filter_by(recipe_id=recipe.id).all()
        average_rating = sum(r.value for r in ratings) / len(ratings) if ratings else 0
        average_ratings[recipe.id] = round(average_rating, 2)
        number_ratings[recipe.id] = len(ratings)
    return render_template('main/view_user_rated_recipes.html', rated_recipes=rated_recipes, average_ratings=average_ratings, user=user, number_ratings=number_ratings)






