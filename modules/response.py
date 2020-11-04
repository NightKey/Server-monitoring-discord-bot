class response:
    codes = {"Bad request": 1, "Success": 2, "Internal error":3, "Denied":4, "Accepted":5}
    def __init__(self, Response, Data=None):
        """Possible Responses: Bad request, Success, Internal error
        """
        self.Response = Response
        self.Data = Data
        self.Code = response.codes[Response]

    def create_altered(self, Response = None, Data = None):
        return response(Response or self.Response, Data or self.Data)