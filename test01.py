import numpy as geek

array = geek.arange(8)
print("Original array : \n", array)

# shape array with 2 rows and 4 columns
array = geek.arange(8).reshape(2, 4)
print("\narray reshaped with 2 rows and 4 columns : \n", array)

# shape array with 2 rows and 4 columns
array = geek.arange(8).reshape(4, 2)
print("\narray reshaped with 2 rows and 4 columns : \n", array)

# Constructs 3D array
array = geek.arange(8).reshape(2, 2, 2)
print("\nOriginal array reshaped to 3D : \n", array)

array = geek.arange(8).reshape(-1, 2)
print("\n : \n", array)

array02 = geek.asarray([[1,2], [1,3], [2,2], [2,3], [3,1], [3,2]])
array03 = array.reshape(-1,2)[array02]
print("\n", array03)

a = geek.array([[1,2], [2,3]])
b = geek.array([[3], [4]])
c = geek.hstack((a,b))
print("\n", c)
d = geek.array([[10,21], [12,13]])
e = a + d
print("\n", e)
f = e/2
print("\n", f)

