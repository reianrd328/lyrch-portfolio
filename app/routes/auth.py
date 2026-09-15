import secrets
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, ActivityLog

auth_bp = Blueprint("auth", __name__)

SESSION_HEARTBEAT_TIMEOUT_SECONDS = 40  # Inactivity threshold before session is deemed closed/abandoned

def _get_device_description(req) -> str:
    """Creates a human-readable identifier of the accessing device/browser."""
    platform = getattr(req.user_agent, "platform", "") or "Unknown OS"
    browser = getattr(req.user_agent, "browser", "") or "Browser"
    ip = req.headers.get("X-Forwarded-For", req.remote_addr or "127.0.0.1").split(",")[0].strip()
    return f"{platform.capitalize()} / {browser.capitalize()} ({ip})"

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("admin.dashboard"))

    active_conflict = False
    conflicting_device = ""
    prefill_username = ""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        force_takeover = bool(request.form.get("force_takeover"))
        prefill_username = username

        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()

        if user and user.check_password(password):
            now = datetime.utcnow()
            current_sess_token = session.get("admin_session_token")

            # Check if active on another device
            if user.active_session_token and user.active_session_heartbeat:
                elapsed = (now - user.active_session_heartbeat).total_seconds()
                # Active if heartbeat within threshold AND token is not our current browser's token
                if elapsed < SESSION_HEARTBEAT_TIMEOUT_SECONDS and user.active_session_token != current_sess_token:
                    if not force_takeover:
                        conflicting_device = user.active_session_device or "Another Computer/Device"
                        active_conflict = True
                        flash(
                            f"SECURITY LOCK: Admin Command Center is currently active on {conflicting_device}. "
                            "Simultaneous access from multiple computers/devices is prohibited. "
                            "Please close the admin window on that computer first, or select 'Force disconnect other device' below.",
                            "danger"
                        )
                        return render_template(
                            "auth/login.html",
                            active_conflict=active_conflict,
                            conflicting_device=conflicting_device,
                            prefill_username=prefill_username
                        )

            # Issue new unique single-device session token
            new_token = secrets.token_hex(24)
            device_desc = _get_device_description(request)

            user.active_session_token = new_token
            user.active_session_device = device_desc
            user.active_session_heartbeat = now
            user.active_session_ip = request.remote_addr
            user.last_login = now
            db.session.commit()

            session["admin_session_token"] = new_token
            session.permanent = True
            login_user(user, remember=True)

            log = ActivityLog(
                title=f"Admin session opened on {device_desc}",
                activity_type="project",
                time_label="Just now"
            )
            db.session.add(log)
            db.session.commit()

            flash(f"Welcome back, Commander {user.display_name}. Single-device lock engaged.", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("admin.dashboard"))
        else:
            flash("Invalid credentials or clearance level denied.", "danger")

    return render_template(
        "auth/login.html",
        active_conflict=active_conflict,
        conflicting_device=conflicting_device,
        prefill_username=prefill_username
    )

@auth_bp.route("/heartbeat", methods=["POST"])
@login_required
def heartbeat():
    """Receives periodic ping from the active admin window to verify lock validity."""
    sess_token = session.get("admin_session_token")
    if not sess_token or sess_token != current_user.active_session_token:
        # If DB token is None but browser is authenticated with token, heal it
        if sess_token and not current_user.active_session_token:
            current_user.active_session_token = sess_token
            current_user.active_session_heartbeat = datetime.utcnow()
            try:
                db.session.commit()
                return jsonify({"status": "ok"})
            except Exception:
                db.session.rollback()
        return jsonify({"status": "revoked", "message": "Session invalidated or opened on another device."}), 401

    current_user.active_session_heartbeat = datetime.utcnow()
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return jsonify({"status": "ok"})

@auth_bp.route("/close-session", methods=["POST"])
def close_session():
    """Called via navigator.sendBeacon when the admin window or tab is closed."""
    if current_user.is_authenticated:
        sess_token = session.get("admin_session_token")
        if sess_token and sess_token == current_user.active_session_token:
            current_user.active_session_token = None
            current_user.active_session_heartbeat = None
            db.session.commit()
        session.pop("admin_session_token", None)
        logout_user()
    return jsonify({"status": "closed"})

@auth_bp.route("/logout")
@login_required
def logout():
    sess_token = session.get("admin_session_token")
    if sess_token and sess_token == current_user.active_session_token:
        current_user.active_session_token = None
        current_user.active_session_heartbeat = None
        db.session.commit()

    session.pop("admin_session_token", None)
    logout_user()

    reason = request.args.get("reason")
    if reason == "conflict":
        flash("Admin session terminated because another device has taken over the clearance.", "warning")
    else:
        flash("Session terminated. Command clearance revoked.", "info")
    return redirect(url_for("public.home"))

