from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from random import choice
import requests
from flask_wtf import FlaskForm
from wtforms.fields import StringField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired
from werkzeug.utils import secure_filename


app = Flask(__name__)

#Connect to Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cafes.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
API_KEY = "ranahafez"
db = SQLAlchemy(app)
app.secret_key = "some secret string"

#Cafe TABLE Configuration
class Cafe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), unique=True, nullable=False)
    map_url = db.Column(db.String(500), nullable=False)
    img_url = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(250), nullable=False)
    seats = db.Column(db.String(250), nullable=False)
    has_toilet = db.Column(db.Boolean, nullable=False)
    has_wifi = db.Column(db.Boolean, nullable=False)
    has_sockets = db.Column(db.Boolean, nullable=False)
    can_take_calls = db.Column(db.Boolean, nullable=False)
    coffee_price = db.Column(db.String(250), nullable=True)

    def to_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns}


class CafeForm(FlaskForm):
    name = StringField('name', validators=[DataRequired()])
    map = StringField('map', validators=[DataRequired()])
    img = StringField('img', validators=[DataRequired()])
    loc = StringField('Location', validators=[DataRequired()])
    seats = StringField('Number of Seats', validators=[DataRequired()])
    toilet = BooleanField("Does it have toilet?..")
    wifi = BooleanField("Does it have wifi?..")
    sockets = BooleanField("Does it have sockets?..")
    calls = BooleanField("Does it have calls?..")
    price = StringField('price', validators=[DataRequired()])
    submit = SubmitField(label="Add Cafe")


class UpdateForm(FlaskForm):
    new_price = StringField('new_price', validators=[DataRequired()])
    submit = SubmitField(label="Update Cafe")

@app.route("/")
def home():
    all_cafes = all()
    cafes = all_cafes.json["cafes"]
    print(cafes)
    return render_template("index.html", cafes=cafes)


@app.route("/get-cafe", methods=["POST", "GET"])
def get_cafes():
    print("here")
    loc = request.form.get("loc")
    if loc:
        req = requests.get(f"http://127.0.0.1:5000/search?loc={loc}")
        if req.status_code == 200:
            req.raise_for_status()
            print(req.json()["cafe"])
            return render_template("index.html", cafes=req.json()["cafe"])
        return "<h1>Error</h1>"
    return "<h1>Please Provide a Location</h1>"


@app.route("/post/<id>")
def get_cafe(id):
    cafe = Cafe.query.get(int(id))
    print(cafe.to_dict())
    return render_template("cafe.html", cafe=cafe)


@app.route("/add", methods=["GET", "POST"])
def add_cafe():
    cafe_form = CafeForm()
    if request.method == "POST":
        if cafe_form.validate_on_submit():
            cafe = post_cafe()
            print(cafe.json)
            return redirect(url_for('home'))
    return render_template('add.html', form=cafe_form)


@app.route("/delete/<id>")
def delete(id):
    req = requests.delete(
        f"http://127.0.0.1:5000/report-closed/{id}",
        params={
            "api_key": API_KEY
        }
    )
    print(req.status_code)
    return redirect(url_for('home'))


@app.route("/update/<id>", methods=["GET", "PATCH", "POST"])
def update_call(id):
    print("update_call here")
    update_form = UpdateForm()
    if request.method == "POST":
        print("This is post .. ")
        print(request.form.get("new_price"))
        req = requests.patch(
            url=f"http://127.0.0.1:5000/update-price/{id}",
            params={
                "new_price": request.form.get("new_price")
            }
        )
        req.raise_for_status()
        return redirect(url_for("home"))
    return render_template("update.html",id=id, form=update_form)


@app.route("/random")
def random_cafe():
    all_cafes = db.session.query(Cafe).all()
    cafe = choice(all_cafes)
    return jsonify(cafe=cafe.to_dict())


# HTTP GET - Read Record
@app.route("/all")
def all():
    all_cafes = db.session.query(Cafe).all()
    cafes = [cafe.to_dict() for cafe in all_cafes]
    return jsonify(cafes=cafes)


@app.route("/search")
def search():
    loc = request.args.get("loc")
    if loc:
        cafe = db.session.query(Cafe).filter_by(location=loc).all()
        if cafe:
            cafes = [c.to_dict() for c in cafe]
            return jsonify(cafe=cafes)
        return jsonify(error={"error_message": "No Cafe in That location."}), 404
    return jsonify(error={"error_message": "There is no location provided."})


# HTTP POST - Create Record
@app.route("/add", methods=["POST"])
def post_cafe():
    if request.method == "POST":
        new_cafe = Cafe(
            name=request.form.get("name"),
            map_url=request.form.get("map"),
            img_url=request.form.get("img"),
            location=request.form.get("loc"),
            seats=request.form.get("seats"),
            has_toilet=int(bool(request.form.get("toilet"))),
            has_wifi=int(bool(request.form.get("wifi"))),
            has_sockets=int(bool(request.form.get("sockets"))),
            can_take_calls=int(bool(request.form.get("calls"))),
            coffee_price=request.form.get("price"),
        )
        print(new_cafe.coffee_price)
        db.session.add(new_cafe)
        db.session.commit()
        return jsonify(response={"success": "A new Cafe was Created."})


# HTTP PUT/PATCH - Update Record
@app.route("/update-price/<int:cafe_id>", methods=["PATCH"])
def update_price(cafe_id):
    price = request.args.get("new_price")
    if price:
        cafe = Cafe.query.get(cafe_id)
        if cafe:
            cafe.coffee_price = price
            db.session.commit()
            return jsonify(success="Successfully updated the price")
        else:
            return jsonify(error={
                "Not Found": "Sorry a cafe with that id was not found in the database"
            })
    return jsonify(error={
        "No Price": "No Price Provided"
    })


# HTTP DELETE - Delete Record
@app.route("/report-closed/<int:cafe_id>", methods=["DELETE"])
def delete_cafe(cafe_id):
    sent_key = request.args.get("api_key")
    if sent_key == API_KEY:
        cafe = Cafe.query.get(cafe_id)
        if cafe:
            db.session.delete(cafe)
            db.session.commit()
            return jsonify(success="Successfully Deleted.")
        else:
            return jsonify(error={
                "No Cafe": "No Cafe with the id Provided"
            })
    return jsonify(error={
        "Not Allowed": "You are not Allowed to use this method"
    })


if __name__ == '__main__':
    app.run(debug=True)
