#!/usr/bin/env python3

from keras.datasets import mnist
from keras.models import Sequential, load_model
from keras.layers import Dense, Dropout, Activation
from keras.utils import to_categorical

import matplotlib.pyplot as plt
import random
import os, sys

# Read in the mnist dataset, images of single digits.
# x_train is a set of images;
# y_train is the data about which image is which digit.
# Same for x_test, y_test -- validation data.
(x_train, y_train), (x_test, y_test) = mnist.load_data()

# The neural net expects floats between 0-1, not integers.
x_train = x_train.astype('float32')
x_train = x_train/255.

x_test = x_test.astype('float32')
x_test = x_test/255.

# Ys are integers between 0 and 9. That's not a very wide range.
# Instead, make an array of probabilities of each digit.
y_train = to_categorical(y_train, 10)
y_test = to_categorical(y_test, 10)

# Reshape the images from 28x28 to a linear array of 784.
# The first dimension will be 60000 for x_train, 10000 for y_train,
# but you can use -1 to base it on the actual size of the input data.
x_train = x_train.reshape(-1, 784)
x_test = x_test.reshape(-1, 784)

def train_model(filename, epochs):
    '''Train the model. When finished, save the result to a file.
       Return the model.
    '''
    # Create the model.
    model = Sequential()

    # Build a layer.
    # A dense layer is a bunch of neurons densely connected to the neurons
    # in the previous layer. That's in contrast to convolutional
    # (there's apparently no "sparse" layer type).
    model.add(Dense(200, input_shape=(784,)))

    # Add a dropout layer, which will randomly drop out some data.
    # That helps keep the model from memorizing the dataset.
    # The dropout will happen after the first layer.
    # .2 is kind of small as a dropout fraction, but we're just making
    # a small test model of 200 neurons so we don't have a lot to spare.
    model.add(Dropout(0.2))

    # Add an activation.
    # Sigmoid isn't actually the right model to use for this problem.
    # RELU, rectified linear units, might be better.
    model.add(Activation('sigmoid'))

    # Add another dense layer. No need to define the input shape
    # this time, since it'll get that from the previous layer.
    # 100 is the output size.
    model.add(Dense(100))

    model.add(Activation('sigmoid'))

    # Another layer the size of our output.
    model.add(Dense(10))

    # A softmax activation layer will give us a list of probabilities
    # that add to 1, so we can see the distribution of probabilities
    # that an image is a particular digit.
    model.add(Activation('softmax'))

    model.summary()

    # Compile the model, giving it an optimizer and a loss function.
    # categorical_crossentropy will output a number indicating how sure
    # it is about the match.
    model.compile(optimizer='adam', loss='categorical_crossentropy',
                  metrics=['accuracy'])

    # Run the model.
    hist = model.fit(x_train, y_train, epochs=epochs, batch_size=100,
                     validation_data=(x_test, y_test))

    print("History:", hist)

    # You can train a model on a fast machine, then save it and load it
    # on something like a Pi.
    model.save(filename)

    return model

# If the model has already been trained, read it in from the file.
# Otherwise, train it and save it to a file.

filename = "mnist_model.h5"

if os.path.exists(filename):
    print("Loading model from %s ..." % filename)
    model = load_model(filename)
else:
    print("Training model ...")
    model = train_model(filename, 10)

# print(x_train.shape)
x_train_images = x_train.reshape(-1, 28, 28)

def key_press(e):
    '''Exit on ctrl-q. q without ctrl dismisses this plot and shows
       the next one.
    '''
    if e.key == 'ctrl+q':
        sys.exit(0)

# Loop: choose random images from the dataset.
# Show the image and a bar chart of what the model predicts.
while True:
    which = random.randint(0, len(x_train))
    prediction = model.predict(x_train[which:which+1])[0]
    # print(prediction)

    ax1 = plt.subplot(211)
    ax1.imshow(x_train_images[which])
    ax2 = plt.subplot(212)
    ax2.bar(range(len(prediction)), prediction)
    # Connect a key handler, so that Ctrl-Q will break out of the loop:
    plt.figure(1).canvas.mpl_connect('key_press_event', key_press)
    plt.show()

