def is_mod(plugin, user_id):
    if user_id in plugin.config.modUserIDs:
        return True
    return False
