"""🎬 Movie Recommender System (Streamlit)"""

import base64
import pickle
from pathlib import Path

import pandas as pd
import requests
import streamlit as st

# ─────────────────────────────────────────────────────────────
# Page config (must be the first Streamlit call)
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Movie Recommender",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
BACKGROUND_IMAGE = "bg3.jpeg"
TMDB_API_KEY = "8265bd1679663a7ea12ac168da84d2e8"  # TODO: move to st.secrets
TMDB_MOVIE_URL = "https://api.themoviedb.org/3/movie/{}?api_key={}&language=en-US"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500/"
PLACEHOLDER = "https://via.placeholder.com/300x450?text=No+Poster"

PAGE_SIZE = 15        # movies added per "Show more" click
SEARCH_LIMIT = 30     # max results shown while searching
NUM_RECOMMENDATIONS = 5

# ─────────────────────────────────────────────────────────────
# Styling
# ─────────────────────────────────────────────────────────────
CSS_TEMPLATE = """
<style>
/* Background */
.stApp {
    background-image:
        radial-gradient(ellipse at center, rgba(8,4,20,0.80) 0%, rgba(8,4,20,0.35) 100%),
        url("data:image/MIME;base64,ENCODED");
    background-size: cover;
    background-position: center;
    background-attachment: fixed;
}
header[data-testid="stHeader"] { background: transparent; }

/* Select box */
div[data-baseweb="select"] > div {
    background-color: rgba(30, 25, 50, 0.65);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(150, 90, 255, 0.35);
}

/* Primary buttons */
div.stButton > button {
    background: linear-gradient(90deg, #7c3aed, #a855f7);
    color: white;
    border: none;
}

/* Dropdown toggle button */
div[class*="st-key-toggle"] button {
    background: rgba(30, 25, 50, 0.6) !important;
    background-image: none !important;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 165, 0, 0.45) !important;
    color: white !important;
    font-weight: 400 !important;
}
div[class*="st-key-toggle"] button:hover {
    background: rgba(50, 40, 80, 0.7) !important;
    border: 1px solid rgba(255, 165, 0, 0.8) !important;
}

/* Movie rows inside the dropdown */
div[class*="st-key-pick_"] button,
div[class*="st-key-more"] button {
    background: transparent !important;
    background-image: none !important;
    border: none !important;
    color: white !important;
    font-weight: 400 !important;
    justify-content: flex-start;
}
div[class*="st-key-pick_"] button:hover,
div[class*="st-key-more"] button:hover {
    background: rgba(255, 165, 0, 0.18) !important;
}
</style>
"""


def set_background(filename: str) -> None:
    """Apply the background image and custom widget styling."""
    img_path = Path(__file__).parent / filename

    if not img_path.exists():
        st.warning(f"Background image not found: {img_path}")
        return

    ext = img_path.suffix.lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext
    encoded = base64.b64encode(img_path.read_bytes()).decode()

    css = CSS_TEMPLATE.replace("MIME", mime).replace("ENCODED", encoded)
    st.markdown(css, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# Data loading
# ─────────────────────────────────────────────────────────────
@st.cache_resource
def load_data():
    with open("movie_dict.pkl", "rb") as f:
        movies = pd.DataFrame(pickle.load(f))
    with open("similarity.pkl", "rb") as f:
        similarity = pickle.load(f)
    return movies, similarity


# ─────────────────────────────────────────────────────────────
# Recommendation logic
# ─────────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def fetch_poster(movie_id):
    """Return the TMDB poster URL for a movie, or None if unavailable."""
    url = TMDB_MOVIE_URL.format(movie_id, TMDB_API_KEY)
    data = requests.get(url).json()
    poster_path = data.get("poster_path")
    return TMDB_IMAGE_BASE + poster_path if poster_path else None


def recommend(title):
    """Return (titles, posters) of the most similar movies."""
    idx = movies[movies["title"] == title].index[0]
    ranked = sorted(enumerate(similarity[idx]), reverse=True, key=lambda x: x[1])
    top = ranked[1 : NUM_RECOMMENDATIONS + 1]

    titles, posters = [], []
    for i, _ in top:
        row = movies.iloc[i]
        titles.append(row.title)
        posters.append(fetch_poster(row.movie_id))
    return titles, posters


# ─────────────────────────────────────────────────────────────
# Session state & callbacks
# ─────────────────────────────────────────────────────────────
def init_state():
    st.session_state.setdefault("option", movies["title"].iloc[0])
    st.session_state.setdefault("limit", PAGE_SIZE)
    st.session_state.setdefault("open", False)


def toggle():
    st.session_state.open = not st.session_state.open


def choose(title):
    st.session_state.option = title
    st.session_state.open = False


def show_more():
    st.session_state.limit += PAGE_SIZE


# ─────────────────────────────────────────────────────────────
# UI components
# ─────────────────────────────────────────────────────────────
def render_movie_picker(option):
    """Dropdown-style picker with search, posters and pagination."""
    st.markdown(
        "<div style='font-size:15px; margin-bottom:4px;'>✨ Select Your Favourite Movie</div>",
        unsafe_allow_html=True,
    )

    arrow = "▲" if st.session_state.open else "▼"
    st.button(f"{option}   {arrow}", key="toggle", on_click=toggle, use_container_width=True)

    if not st.session_state.open:
        return

    with st.container(height=420, border=True):
        query = st.text_input(
            "Search", placeholder="Type a movie name…", label_visibility="collapsed"
        )

        if query:
            matches = movies[
                movies["title"].str.contains(query, case=False, na=False, regex=False)
            ]
            results = matches.head(SEARCH_LIMIT)
        else:
            results = movies.head(st.session_state.limit)

        if results.empty:
            st.write("No movie found.")

        for _, row in results.iterrows():
            c1, c2 = st.columns([1, 6], vertical_alignment="center")
            with c1:
                st.image(fetch_poster(row.movie_id) or PLACEHOLDER, width=50)
            with c2:
                label = ("✓ " if row.title == option else "") + row.title
                st.button(
                    label,
                    key=f"pick_{row.movie_id}",
                    on_click=choose,
                    args=(row.title,),
                )

        if not query and st.session_state.limit < len(movies):
            st.button("Show more movies ▼", key="more", on_click=show_more)


def render_prompt(option) -> bool:
    """Show the confirmation line and return True if the button was clicked."""
    with st.container(horizontal=True, vertical_alignment="center"):
        st.markdown(
            f"""
            <p style="font-size: 19px; margin: 0;">
                <span style="color: orange; font-weight: bold;">{option}</span>
                is a great movie. Ready to discover similar movies?
            </p>
            """,
            unsafe_allow_html=True,
        )
        return st.button("YES")


def render_recommendations(option):
    """Heading plus a row of recommended movie posters."""
    st.markdown(
        f"""
        <h3 style="font-size: 25px; color: white;">
            ⭐ Recommended Movies
            <span style="font-size: 15px; font-weight: normal; color: #A5ABC0;">
                (Because you liked
                <span style="color: orange; font-weight: bold;">{option}</span>)
            </span>:
        </h3>
        """,
        unsafe_allow_html=True,
    )

    titles, posters = recommend(option)
    for col, title, poster in zip(st.columns(NUM_RECOMMENDATIONS), titles, posters):
        with col:
            st.image(poster or PLACEHOLDER)
            st.markdown(f":orange[**{title}**]")


# ─────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────
set_background(BACKGROUND_IMAGE)
movies, similarity = load_data()
init_state()

st.title("🎬Movie :orange[**Recommender**] System")

selected = st.session_state.option
render_movie_picker(selected)

if render_prompt(selected):
    render_recommendations(selected)