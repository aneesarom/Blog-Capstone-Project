import time


def speed_calc_decorator(function):
    current_time = time.time()

    def wrapper_function():
        function()
        delayed_time = time.time()
        print(f"{function.__name__} run speed: {delayed_time - current_time}s")

    return wrapper_function


@speed_calc_decorator
def fast_function():
    for i in range(10000000):
        i * i


@speed_calc_decorator
def slow_function():
    for i in range(10000000):
        i * i


def admin_only(function):
    def wrapper_function():
        if 1 * 1 == 1:
            function()
    return wrapper_function

@admin_only
def check():
    print("working")


check()
# fast_function()
# slow_function()
