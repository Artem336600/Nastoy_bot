from aiogram.fsm.state import State, StatesGroup


class EventForm(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_photo = State()
    waiting_for_board_games = State()
    waiting_for_datetime = State()
    waiting_for_responsible = State()
    waiting_for_quantity = State()


class EventEditForm(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_photo = State()
    waiting_for_board_games = State()
    waiting_for_datetime = State()
    waiting_for_responsible = State()
    waiting_for_quantity = State()


class MessageParticipantForm(StatesGroup):
    waiting_for_message = State()


class BlacklistForm(StatesGroup):
    waiting_for_reason = State()


class MessageBlacklistUserForm(StatesGroup):
    waiting_for_message = State()


class BroadcastForm(StatesGroup):
    waiting_for_message = State()


class FeedbackForm(StatesGroup):
    waiting_for_comment = State()


class GlobalMessageForm(StatesGroup):
    waiting_for_message = State()


class ResponsibleSelectionForm(StatesGroup):
    waiting_for_responsibles = State()


class MessageResponsibleForm(StatesGroup):
    waiting_for_message = State()


class BoardGameCreateForm(StatesGroup):
    waiting_for_photo = State()
    waiting_for_title = State()
    waiting_for_rules = State()
    waiting_prompt_message = State()


