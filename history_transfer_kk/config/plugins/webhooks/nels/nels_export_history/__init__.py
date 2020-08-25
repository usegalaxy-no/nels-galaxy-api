def main(trans, webhook, params):
    try:
        if trans.user:
            hist = trans.get_history()
            if (hist):
                historyid = trans.security.encode_id(hist.id)
                userid = trans.security.encode_id(trans.user.id)
                return {'userid': userid, 'username': trans.user.username, "email": trans.user.email, "history": historyid, "historyname": hist.name}
            else:
                return {'error': 'No history to export'}
        else:
            return {'error': "User not logged in"}
    except:
        return {'error': sys.exc_info()[0]}
