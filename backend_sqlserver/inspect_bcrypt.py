import bcrypt
import passlib
import passlib.handlers.bcrypt as pb

print('bcrypt file', bcrypt.__file__)
print('bcrypt has __about__', hasattr(bcrypt, '__about__'))
print('bcrypt attrs', [a for a in dir(bcrypt) if 'about' in a.lower()])
print('passlib version', passlib.__version__)
print('pb', pb)
