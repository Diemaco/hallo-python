def foreach(classIn):
    for cls in classIn.__subclasses__():
        try:
            raise cls()
        except BaseException as e:
            print(f'Mission failed successfully! (Raised {e.__class__.__name__})')
        finally:
            foreach(cls)


if __name__ == '__main__':
    foreach(BaseException)
    raise BaseException()
