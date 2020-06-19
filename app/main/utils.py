from datetime import datetime
from typing import Any, Optional, Tuple
from werkzeug.wrappers import Response

from flask import jsonify, url_for, redirect, flash, request
from flask_login import current_user

from app.models import db, ChannelAllowList, Message, User, Channel
from app.models.channel_allowlist import UserRole

from app.sockets.sockets import announce_channel, announce_message
from app.bcrypt.utils import hash_password, check_hashed_password

from app.forms.channel import UpdateChannelForm, AddChannelForm, JoinChannelForm
"""
Utility functions for main routes.
"""

def add_channel(channel_name: str) -> None:
    """Add channel to the database and emit it with Socket.IO.

    Args:
        channel_name: Name of the channel to be added.

    """
    db.session.add(Channel(name=channel_name))
    db.session.commit()
    announce_channel(channel_name)

def pretty_time(full_time: datetime) -> str:
    """Take datetime object and get its string of the form YYYY-MM-DD HH:MM.

    Args:
        full_time: DateTime object which pretty form the function should return.

    Returns:
        String YYYY-MM-DD HH:MM.

    """
    full_time_str = str(full_time)
    length_boundary = len('2020-01-01 00:00')
    return full_time_str[:length_boundary]

def get_messages(channel_name: str, counter: int) -> Any:
    """Get the messages of the given channel and return them in JSON format.
    The function supports dynamic loading and will return only a specified number of messages.
    The last message to be loaded is given by the argument "counter".

    Args:
        channel_name: Name of the channel which messages the function should look for.
        counter: Id of the last message to be displayed.

    Returns:
        JSON response with all data about messages of the channel.

    """
    num_messages_loaded_at_once = 20

    channel = Channel.query.filter_by(name=channel_name).first()
    messages = channel.messages

    messages_response = [
        {
            'userName': User.query.filter_by(id=message.user_id).first().username,
            'userPicture': f"{url_for('static', filename='img/profile_pictures')}/"
                           f"{ User.query.filter_by(id=message.user_id).first().profile_picture }",
            'content': message.content,
            'time': pretty_time(message.time)
        }
        for message in messages[max(counter - num_messages_loaded_at_once, 0):counter]
    ]
    return jsonify({'messages': messages_response})

def add_message(message_content: str, channel: str) -> None:
    """Add the given message to the given channel in database. Emit the message with Socket.IO
    after adding it.

    Args:
        message_content: Content of the message to be added.
        channel: Channel the message should be added to.

    """
    username = current_user.username
    user_id = current_user.id
    user_picture = f"{url_for('static', filename='img/profile_pictures')}/{ current_user.profile_picture }"

    full_time = datetime.now()

    channel_id = Channel.query.filter_by(name=channel).first().id

    db.session.add(Message(
        content=message_content, user_id=user_id, time=full_time, channel_id=channel_id
    ))

    db.session.commit()
    announce_message(username, user_picture, pretty_time(full_time), channel, message_content)

def is_valid_channel(channel: Optional[Channel], form: AddChannelForm) -> bool:
    """Check if the given channel exists and then check if the password provided in the "join channel" form
    matches this channel's password in the database.

    Args:
        channel: None or the channel in the database.
        form: The filled "join channel" form.

    Returns:
        True if the channel is valid, false otherwise.

    """
    if isinstance(channel, Channel):
        return check_hashed_password(channel.password, form.password.data)
    else:
        return False

def process_add_channel_form(form: AddChannelForm) -> Response:
    """Get the validated form to add a channel. Hash the given password of the channel.
    Set the current user admin role on this channel. Save all of that in the database.

    Args:
        form: The filled form to add a channel.

    """
    hashed_password = hash_password(form.password.data)

    db.session.add(Channel(
        name=form.name.data, password=hashed_password
    ))

    channel_id = Channel.query.filter_by(password=hashed_password).first().id

    db.session.add(ChannelAllowList(
        channel_id=channel_id, user_id=current_user.id, user_role=UserRole.ADMIN.value
    ))

    db.session.commit()

    flash(f'You have successfully added the channel "{form.name.data}!"', 'success')

    return redirect(url_for('main.setup_app'))

def process_join_channel_form(form: JoinChannelForm) -> str:
    channel = Channel.query.filter_by(name=form.name.data).first()

    if is_valid_channel(channel, form):
        db.session.add(ChannelAllowList(
            channel_id=channel.id, user_id=current_user.id
        ))
        db.session.commit()
        flash(f'You have successfully joined the channel "{channel.name}"!', 'success')
    else:
        flash('Joining unsuccessful! Incorrect channel name or password.', 'danger')

    return redirect(url_for('main.setup_app'))

def process_update_channel_form(form: UpdateChannelForm):
    pass

def get_number_of_channels_users(channel: Channel) -> int:
    return ChannelAllowList.query.filter_by(channel_id=channel.id).count()

def get_number_of_channels_messages(channel: Channel) -> int:
    return len(channel.messages)

def get_channels_users(channel: Channel) -> Tuple[User]:
    channel_allowed_records = ChannelAllowList.query.filter_by(channel_id=channel.id).all()
    return [User.query.get(record.user_id) for record in channel_allowed_records]

def is_admin(channel: Channel, user: User) -> bool:
    allowed_record = (ChannelAllowList.query.filter_by(channel_id=channel.id)
                      .filter_by(user_id=user.id).first())
    return allowed_record and allowed_record.user_role == UserRole.ADMIN.value

def check_channel_settings_form(channel_id: str, user: str) -> Optional[Tuple[Channel, User]]:
    if not channel_id or not user:
        print(f"invalid function's params: channel_id={channel_id}, user={user}")
        return None

    try:
        channel_id = int(channel_id)
        user_id = int(user)
    except ValueError:
        print(f"This values are not integers: channel_id={channel_id}, user={user}")
        return None

    channel = Channel.query.get(channel_id)

    if not channel:
        print(f"No channel: {channel}")
        return None

    user = User.query.get(user_id)

    if not user:
        print(f"No user: {user}")
        return None

    if not is_admin(channel, current_user):
        print(f"Current user is not admin: {current_user} on {channel}")
        return None
    else:
        return channel, user

def admin_manager(command: str, channel_id: str, user_id: str):
    checked_value = check_channel_settings_form(channel_id, user_id)

    if not checked_value:
        return admin_invalid()
    else:
        channel, user = checked_value

    allow_record = (ChannelAllowList.query.filter_by(channel_id=channel_id)
                    .filter_by(user_id=user_id).first())

    if not allow_record:
        print(f"There is no allow_record: {allow_record}")
        return admin_invalid()

    print(f"The command is {command}")
    if command == 'make':
        allow_record.user_role = UserRole.ADMIN.value
        db.session.commit()
        message = 'has just become'
    elif command == 'revoke':
        allow_record.user_role = UserRole.NORMAL_USER.value
        db.session.commit()
        message = 'no longer'
    else:
        return admin_invalid()

    flash(f'The user {User.query.get(user_id).username} {message} admin of this channel.', 'success')
    return redirect(f'channel/{Channel.query.get(channel_id).name}')

def admin_invalid() -> str:
    flash("It wasn't possible to modify the role of the given user.", 'danger')
    return redirect(url_for('main.setup_app'))