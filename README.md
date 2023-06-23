# Configurun
Configurun is a pyside6-based packge that implements several tools for managing, creating and running python configurations. 
It was designed mainly with machine-learning tasks in mind, but can be used for running any kind of python code using configurations.

The goal of this package is to make it easier to manage complex configurations and to be able to queue & run the configurations on a remote system in a simple and efficient way.
The configurun-app is especially useful for long argparse-based scripts. This package was created in tandem with [pyside6-utils](https://github.com/Woutah/pyside6-utils/).


The app's configuration-input is built around python `@dataclass` objects, and their `field()` properties. We can either provide a custom `@dataclass` with all attributes we would like to edit, or directly pass an existing `argparse.Argumentparser` object to the app-creator. 

