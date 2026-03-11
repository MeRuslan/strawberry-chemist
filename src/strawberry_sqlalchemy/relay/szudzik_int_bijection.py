import math


def elegant_pair(x, y):
    return (x * x + x + y) if (x >= y) else (y * y + x)


def elegant_unpair(z):
    sqrtz = math.floor(math.sqrt(z))
    sqz = sqrtz * sqrtz
    return [sqrtz, z - sqz - sqrtz] if ((z - sqz) >= sqrtz) else [z - sqz, sqrtz]
