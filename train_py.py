# -*- coding: utf-8 -*-
"""train.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1b-cSI3ZlseaPuo9ze8kdi_MY2UWy72js


# Libraries
"""

from keras.datasets import fashion_mnist, mnist
from tqdm.notebook import tqdm
import numpy as np
import matplotlib.pyplot as plt
import math
import copy
from sklearn.model_selection import train_test_split 
import pandas as pd
import subprocess
subprocess.call(['pip', 'install', 'wandb'])
import wandb
wandb.login()

"""# Data Processing"""

class OneHotEncoder_from_scratch:
    
    def __init__(self):
        self.categories = None
    def fit(self, X):
        self.categories =[]
        for i in range(X.shape[1]):
            feature_categories =list(set(X[:, i]))
            self.categories.append(feature_categories)
            
    def transform(self, X):
        one_hot_vector = []

        for i in range(X.shape[0]):
            one_hot_row = []
            for j in range(X.shape[1]):

                category_index = self.categories[j].index(X[i, j])
                category_one_hot =[0] *len(self.categories[j])
                category_one_hot[category_index] = 1

                one_hot_row.extend(category_one_hot)
            one_hot_vector.append(one_hot_row)
        return np.array(one_hot_vector)

dataset = 'fashion_mnist'

def dataset_type(dataset):
  if dataset == 'fashion_mnist':
      (train_images, train_labels), (test_images, test_labels) = fashion_mnist.load_data()
  elif dataset == 'mnist':
      (train_images, train_labels), (test_images, test_labels) = mnist.load_data()
  else:
      raise ValueError('Invalid dataset name')
  X_train, X_val, Y_train, Y_val = train_test_split(train_images, train_labels, test_size=0.1, random_state=42)
  train_input = []
  for i in range(len(X_train)):
      train_input.append(list(np.concatenate(X_train[i]).flat))

  val_input = []
  for i in range(len(X_val)):
      val_input.append(list(np.concatenate(X_val[i]).flat))

  test_input = []
  for i in range(len(test_images)):
      test_input.append(list(np.concatenate(test_images[i]).flat))
  Y_train = np.array(Y_train)
  Y_val = np.array(Y_val)
  Y_test = np.array(test_labels)

  X_train = np.array(train_input) / 255.0
  X_test = np.array(test_input) / 255.0
  X_val = np.array(val_input) / 255.0

  enc = OneHotEncoder_from_scratch()
  enc.fit(Y_train.reshape(-1, 1))
  Y_train = enc.transform(Y_train.reshape(-1, 1))
  Y_val = enc.transform(Y_val.reshape(-1, 1))
  Y_test = enc.transform(Y_test.reshape(-1, 1))

  return X_train, X_val, X_test, Y_train, Y_val, Y_test

dataset = 'fashion_mnist'
X_train, X_val, X_test, Y_train, Y_val, Y_test = dataset_type(dataset)

# print(Y_train.shape, Y_val.shape, Y_test.shape)
# print(X_train.shape, X_val.shape, X_test.shape)

"""# FFNW Class"""

wandb.init(project = 'Train_py', entity = 'ed22s009')

class FFNN:
  def __init__(self, X, Y,
               epochs = 100, 
               hidden_layer_count = 4,
               hidden_layers =  [32, 64, 128, 256],
               learning_rate = 0.001,
               batch_size = 32,
               activation='tanh',
               weight_init='random',
               loss = 'mean_squared_error',
               weight_decay = 0):
    
    self.inputs =X.shape[1] # Number of inputs
    self.outputs= Y.shape[1] # Number of outputs
    self.epochs = epochs
    self.hidden_layers = hidden_layer_count  # Number of hidden layers 
    self.network_size= [self.inputs] + hidden_layers +[self.outputs] # input layer + hidden layers + output layers
    self.learning_rate = learning_rate
    self.batch_size = batch_size
    self.weights={} # It will create dictionary for weights and biases
    self.weights_h = []
    self.num_classes = Y.shape[1]
    self.weight_init = weight_init
    self.activation_function = activation
    self.loss_function = loss
    self.lambd = weight_decay
    np.random.seed(0)  # We will set seed value so that it will generate same random numebers every time

    self.grad_derivatice={}
    self.update_weights={}
    self.prev_update_weights={}
    for i in range(1,self.hidden_layers+1):
      vw_key, vb_key, mb_key, mw_key = [f'{key}{i}' for key in ['vw', 'vb', 'mb', 'mw']]
      self.update_weights[vw_key]=0
      self.update_weights[vb_key]=0
      self.update_weights[mb_key]=0
      self.update_weights[mw_key]=0
      self.prev_update_weights[vw_key]=0
      self.prev_update_weights[vb_key]=0

    
    if self.weight_init == 'random':
      for i in range(1, self.hidden_layers + 2):
          weight_shape = (self.network_size[i - 1], self.network_size[i])
          weight_scale = 0.1
          self.weights[f'W{i}'] = np.random.normal(scale=weight_scale, size=weight_shape)*0.1
          
          bias_shape = (1, self.network_size[i])
          self.weights[f'B{i}'] = np.zeros(bias_shape)

    if self.weight_init == 'Xavier':
      for i in range(1, self.hidden_layers + 2):
          weight_shape = (self.network_size[i - 1], self.network_size[i])
          weight_scale = 0.1
          self.weights[f'W{i}'] = np.random.normal(scale=weight_scale, size=weight_shape)*np.sqrt(1/self.network_size[i-1])
          
          bias_shape = (1, self.network_size[i])
          self.weights[f'B{i}'] = np.zeros(bias_shape)

  def forward_activation(self, X):
      activation_functions = {
          'sigmoid': lambda x: 1.0 / (1.0 + np.exp(-x)),
          'tanh': np.tanh,
          'ReLU': lambda x: np.maximum(0, x)
      }
      activation_function = activation_functions.get(self.activation_function)
      if activation_function:
          return activation_function(X)
      else:
          raise ValueError(f"Unknown activation function '{self.activation_function}'")


  def grad_activation(self, X):
      activation_gradients = {
          'sigmoid': lambda x: x * (1 - x),
          'tanh': lambda x: 1 - np.square(x),
          'ReLU': lambda x: 1.0 * (x > 0)
      }
      gradient_function = activation_gradients.get(self.activation_function)
      if gradient_function:
          return gradient_function(X)
      else:
          raise ValueError(f"Unknown activation function '{self.activation_function}'")

  def softmax(self, X):
    exps =np.exp(X - np.max(X, axis=1, keepdims=True))
    return  exps /np.sum(exps, axis=1, keepdims=True)
  

  def forward_pass(self, X, weights=None):
      if weights is None:
          weights = self.weights
      self.z = {}
      self.z = {}
      self.z[0] = X
      for i in range(self.hidden_layers):
          self.z[i+1] = self.z[i] @ weights[f'W{i+1}'] + weights[f'B{i+1}']
          self.z[i+1] = self.forward_activation(self.z[i+1])
      self.z[self.hidden_layers+1] = self.z[self.hidden_layers] @ weights[f'W{self.hidden_layers+1}'] + weights[f'B{self.hidden_layers+1}']
      self.z[self.hidden_layers+1] = self.softmax(self.z[self.hidden_layers+1])
      return self.z[self.hidden_layers+1]

  def backprop(self, X, Y, weights=None):
    if weights is None:
        weights = self.weights

    self.forward_pass(X, weights)
    self.grad_derivatice = {}
    total_layers= self.hidden_layers + 1

    if self.loss_function == 'cross_entropy':
        self.grad_derivatice[f'dA{total_layers}'] =  (self.z[total_layers] - Y)
    elif self.loss_function == 'mean_squared_error':
        self.grad_derivatice[f'dA{total_layers}'] = (1/X.shape[0]) * 2 * (self.z[total_layers] - Y)

    for k in range(total_layers, 0, -1):
        w_key, b_key, dw_key, db_key, da_key = [f'{key}{k}' for key in ['W', 'B', 'dW', 'dB', 'dA']]
        self.grad_derivatice[dw_key] = np.matmul(self.z[k-1].T, self.grad_derivatice[da_key]) + self.lambd * weights[w_key]
        self.grad_derivatice[db_key] = np.sum(self.grad_derivatice[da_key], axis=0).reshape(1, -1) + + self.lambd * weights[b_key]
        self.grad_derivatice[f'dH{k-1}'] = np.matmul(self.grad_derivatice[da_key], weights[w_key].T)
        self.grad_derivatice[f'dA{k-1}'] = np.multiply(self.grad_derivatice[f'dH{k-1}'], self.grad_activation(self.z[k-1]))

    return self.grad_derivatice[f'dH{k-1}']

  def fit(self, X, Y, X_val, Y_val,algo= 'GD',a = 10, eps=1e-8, beta=0.9, beta1=0.9, beta2=0.9, gamma=0.9, show_loss = False):
    if show_loss:
      los = []
      accuracy = []
    for num_epoch in tqdm(range(1, self.epochs+1), unit='epoch'):
      m = X.shape[0]
      
      if algo == 'sgd':
        for i in range(m):
            rand_idx = np.random.randint(m)
            x_i = X[rand_idx:rand_idx+1]
            y_i = Y[rand_idx:rand_idx+1]
            self.backprop(x_i, y_i)
            for j in range(1, self.hidden_layers+1):
              w_key, b_key, dw_key, db_key = [f'{key}{j}' for key in ['W', 'B', 'dW', 'dB']]
              self.weights[w_key] -=self.learning_rate * self.grad_derivatice[dw_key]
              self.weights[b_key] -=self.learning_rate * self.grad_derivatice[db_key]
        self.wandlog(num_epoch, X, Y, X_val, Y_val)

      elif algo == 'momentum':
        num_examples = X.shape[0]
        num_batches = num_examples //self.batch_size
        for batch in range(num_batches + 1):
            start_index = batch *self.batch_size
            end_index = min((batch+1)*self.batch_size, num_examples)
            X_batch, Y_batch = X[start_index:end_index], Y[start_index:end_index]

            self.backprop(X_batch, Y_batch)

            for i in range(1, self.hidden_layers+1):
              w_key, b_key, vw_key, vb_key,dw_key, db_key = [f'{key}{i}' for key in ['W', 'B', 'vw', 'vb', 'dW', 'dB']]
              self.update_weights[vw_key] = gamma *self.update_weights[vw_key] + self.learning_rate * (self.grad_derivatice[dw_key])
              self.update_weights[vb_key] = gamma *self.update_weights[vb_key] + self.learning_rate * (self.grad_derivatice[db_key])
              self.weights[w_key] -= self.update_weights[vw_key]
              self.weights[b_key] -= self.update_weights[vb_key]
        self.wandlog(num_epoch, X, Y,X_val, Y_val)

      elif algo == 'rmsprop':
        num_examples = X.shape[0]
        num_batches = num_examples //self.batch_size

        for batch in range(num_batches + 1):
            start_index = batch *self.batch_size
            end_index = min((batch+1)*self.batch_size, num_examples)
            X_batch, Y_batch = X[start_index:end_index], Y[start_index:end_index]

            self.backprop(X_batch, Y_batch)

            for i in range(1, self.hidden_layers+1):
                w_key, b_key, vw_key, vb_key, dw_key, db_key = [f'{key}{i}' for key in ['W', 'B', 'vw', 'vb', 'dW', 'dB']]
                self.update_weights[vw_key] = beta * self.update_weights[vw_key] + (1 - beta) * ((self.grad_derivatice[dw_key])**2)
                self.update_weights[vb_key] = beta * self.update_weights[vb_key] + (1 - beta) * ((self.grad_derivatice[db_key])**2)
                self.weights[w_key] -= (self.learning_rate / (np.sqrt(self.update_weights[vw_key] + eps))) * (self.grad_derivatice[dw_key])
                self.weights[b_key] -= (self.learning_rate / (np.sqrt(self.update_weights[vb_key] + eps))) * (self.grad_derivatice[db_key])

        self.wandlog(num_epoch, X, Y, X_val, Y_val)
      
      elif algo == 'adam':

        num_examples = X.shape[0]
        num_batches = num_examples //self.batch_size

        for batch in range(num_batches + 1):
            start_index = batch *self.batch_size
            end_index = min((batch+1)*self.batch_size, num_examples)
            X_batch, Y_batch = X[start_index:end_index], Y[start_index:end_index]

            self.backprop(X_batch, Y_batch)

            for i in range(1, self.hidden_layers + 1):
                w_key, b_key, vw_key, vb_key, mw_key, mb_key = [f'{key}{i}' for key in ['W', 'B', 'vw', 'vb', 'mw', 'mb']]
                dw_key, db_key= [f'{key}{i}' for key in ['dW', 'dB']]

                self.update_weights[mw_key] = beta1 * self.update_weights[mw_key] + (1 - beta1) * self.grad_derivatice[dw_key]
                self.update_weights[vw_key] = beta2 * self.update_weights[vw_key] + (1 - beta2) * (self.grad_derivatice[dw_key] ** 2)
                mw_hat = self.update_weights[mw_key] / (1 - np.power(beta1, batch + 1))
                vw_hat = self.update_weights[vw_key] / (1 - np.power(beta2, batch + 1))
                self.weights[w_key] -= (self.learning_rate / np.sqrt(vw_hat + eps)) * mw_hat

                self.update_weights[mb_key] = beta1 * self.update_weights[mb_key] + (1 - beta1) * self.grad_derivatice[db_key]
                self.update_weights[vb_key] = beta2 * self.update_weights[vb_key] + (1 - beta2) * (self.grad_derivatice[db_key] ** 2)
                mb_hat = self.update_weights[mb_key] / (1 - np.power(beta1, batch + 1))
                vb_hat = self.update_weights[vb_key] / (1 - np.power(beta2, batch + 1))
                self.weights[b_key] -= (self.learning_rate / np.sqrt(vb_hat + eps)) * mb_hat

        self.wandlog(num_epoch, X, Y,X_val, Y_val)
          
      elif algo == 'nag':
        num_examples = X.shape[0]
        num_batches = num_examples //self.batch_size

        temp_weights = {}
        for i in range(1, self.hidden_layers+2):
          w_key, b_key = [f'{key}{i}' for key in ['W', 'B']]
          temp_weights[w_key] = np.zeros_like(self.weights[w_key])
          temp_weights[b_key] = np.zeros_like(self.weights[b_key])
        
        for batch in range(num_batches + 1):
            start_index = batch *self.batch_size
            end_index = min((batch+1)*self.batch_size, num_examples)
            X_batch, Y_batch = X[start_index:end_index], Y[start_index:end_index]

            for i in range(1,self.hidden_layers+1):
                w_key, b_key, vw_key, vb_key,dw_key, db_key = [f'{key}{i}' for key in ['W', 'B', 'vw', 'vb', 'dW', 'dB']]
                self.update_weights[vw_key]=gamma*self.prev_update_weights[vw_key]
                self.update_weights[vb_key]=gamma*self.prev_update_weights[vb_key]
                temp_weights[w_key]=self.weights[w_key]-self.update_weights[vw_key]
                temp_weights[b_key]=self.weights[b_key]-self.update_weights[vb_key]
            self.backprop(X_batch,Y_batch,temp_weights)
            for i in range(1,self.hidden_layers+1):
                w_key, b_key, vw_key, vb_key,dw_key, db_key = [f'{key}{i}' for key in ['W', 'B', 'vw', 'vb', 'dW', 'dB']]
                self.update_weights[vw_key] = gamma *self.update_weights[vw_key] + self.learning_rate * (self.grad_derivatice[dw_key])
                self.update_weights[vb_key] = gamma *self.update_weights[vb_key] + self.learning_rate * (self.grad_derivatice[db_key])
                self.weights[w_key] -= self.learning_rate * (self.update_weights[vw_key]/m)
                self.weights[b_key] -= self.learning_rate * (self.update_weights[vb_key]/m) 

            self.prev_update_weights=self.update_weights

        self.wandlog(num_epoch, X, Y,X_val, Y_val)

      elif algo == 'nadam':

        num_examples = X.shape[0]
        num_batches = num_examples //self.batch_size

        num_updates = 0
        for i in range(1, self.hidden_layers + 1):
            w_key, b_key, vw_key, vb_key, mw_key, mb_key = [f'{key}{i}' for key in ['W', 'B', 'vw', 'vb', 'mw', 'mb']]
            dw_key, db_key, mw_i_key, mb_i_key = [f'{key}{i}' for key in ['dW', 'dB', 'mw_inf', 'mb_inf']]

            for batch in range(num_batches + 1):
                start_index = batch *self.batch_size
                end_index = min((batch+1)*self.batch_size, num_examples)
                X_batch, Y_batch = X[start_index:end_index], Y[start_index:end_index]

                self.backprop(X_batch, Y_batch)

                num_updates += 1
                self.update_weights.setdefault(mw_i_key, 0)
                self.update_weights[mw_key] = beta1 * self.update_weights[mw_key] + (1 - beta1) * (self.grad_derivatice[dw_key] )
                self.update_weights[vw_key] = beta2 * self.update_weights[vw_key] + (1 - beta2) * ((self.grad_derivatice[dw_key]) ** 2)
                mw_hat = self.update_weights[mw_key] / (1 - np.power(beta1, num_updates))
                vw_hat = self.update_weights[vw_key] / (1 - np.power(beta2, num_updates))
                mw_inf = beta1 * self.update_weights[mw_i_key] + (1 - beta1) * np.abs(self.grad_derivatice[dw_key])
                mw_inf_hat = mw_inf / (1 - np.power(beta1, num_updates))
                self.weights[w_key] -= (self.learning_rate / np.sqrt(vw_hat + eps)) * ((beta1 * mw_hat) + ((1 - beta1) * self.grad_derivatice[dw_key])) / (1 - np.power(beta2, num_updates)) + self.learning_rate * eps * np.sqrt(1 - np.power(beta2, num_updates)) * mw_inf_hat

                self.update_weights.setdefault(mb_i_key, 0)
                self.update_weights[mb_key] = beta1 * self.update_weights[mb_key] + (1 - beta1) * (self.grad_derivatice[db_key])
                self.update_weights[vb_key] = beta2 * self.update_weights[vb_key] + (1 - beta2) * ((self.grad_derivatice[db_key]) ** 2)
                mb_hat = self.update_weights[mb_key] / (1 - np.power(beta1, num_updates))
                vb_hat = self.update_weights[vb_key] / (1 - np.power(beta2, num_updates))
                mb_inf = beta1 * self.update_weights[mb_i_key] + (1 - beta1) * np.abs(self.grad_derivatice[db_key])
                mb_inf_hat = mb_inf / (1 - np.power(beta1, num_updates))
                self.weights[b_key] -= (self.learning_rate / np.sqrt(vb_hat + eps)) * ((beta1 * mb_hat) + ((1 - beta1) * self.grad_derivatice[db_key])) / (1 - np.power(beta2, num_updates)) + self.learning_rate * eps * np.sqrt(1 - np.power(beta2, num_updates)) * mb_inf
        self.wandlog(num_epoch, X, Y,X_val, Y_val)
      
      if show_loss:
        loss, acc = self.performance(X_val, Y_val)
        acc = acc
        los.append(loss)
        accuracy.append(acc)



    if show_loss:
   
          max_acc_index = np.argmax(accuracy)


          plt.plot(los, label='Loss')
          plt.plot(accuracy, label='Accuracy')
          plt.plot(max_acc_index, los[max_acc_index], marker='o', color='red')
          plt.plot(max_acc_index, accuracy[max_acc_index], marker='o', color='green')

    
          plt.text(max_acc_index, los[max_acc_index], f'loss @ Max val acc: ( {los[max_acc_index]:.4f})',  va='top')
          plt.text(max_acc_index, accuracy[max_acc_index], f'Max Val acc: ({accuracy[max_acc_index]:.4f})', va='bottom')

          plt.ylim([min(los + accuracy)-0.1, max(los + accuracy) + 0.1])

          plt.title('Val Loss and val Accuracy with {}'.format(self.loss_function))
          plt.xlabel('Epochs')
          plt.ylabel('Loss / Accuracy')
          plt.legend()
          plt.show()


  def predict(self, X):
    Y_pred = (self.forward_pass(X))
    return np.array(Y_pred).squeeze()
  
  def accuracy_score(self, X, Y):
    Y_true = np.argmax(Y, axis=1).reshape(-1, 1)
    pred_labels = np.argmax(self.predict(X), axis=1).reshape(-1,1)
    return np.sum(pred_labels == Y_true) / len(Y)

  def Loss(self, X, Y):
      Y_pred = self.predict(X)
      if self.loss_function == 'cross_entropy':
          loss = -np.mean(Y * np.log(Y_pred + 1e-8))
          max_loss = -np.mean(Y * np.log(1e-8))
      elif self.loss_function == 'mean_squared_error':
          loss = np.mean((Y - Y_pred)**2)
          max_loss = np.mean(Y**2)
      else:
          raise ValueError('Invalid loss function')
      loss = loss / max_loss
      return loss

  def performance(self, X_test, Y_test):
    loss = self.Loss(X_test, Y_test)
    accuracy = self.accuracy_score(X_test, Y_test)
    return loss, accuracy


  def confusion_matrix(self, X, Y):

      actual_labels = np.argmax(Y, axis=1)
      predicted_labels = np.argmax(self.forward_pass(X), axis=1)


      available_classes = np.unique(np.concatenate((actual_labels, predicted_labels)))

      confo_matrix = np.zeros((len(available_classes), len(available_classes)), dtype=int)
      for i, actual in enumerate(available_classes):
          for j, predicted in enumerate(available_classes):
              confo_matrix[i,j] = np.where((actual_labels == actual) & (predicted_labels == predicted))[0].shape[0]
      wandb.log({'confusion_matrix': wandb.plot.confusion_matrix(
          probs=None,
          y_true=actual_labels,
          preds=predicted_labels,
          class_names=list(available_classes),
          title='Confusion Matrix'
      )})

      return confo_matrix


  def confo_matrixplot(self, confusion_matrix, title='Confusion Matrix', cmap='PuBu'):
    confusion_matrix = np.array(confusion_matrix)
    confusion_matrix = confusion_matrix / np.sum(confusion_matrix, axis=1, keepdims=True)
    plt.matshow(confusion_matrix, cmap=cmap)
    plt.colorbar()
    tick_marks = np.arange(len(confusion_matrix))
    plt.xticks(tick_marks)
    plt.yticks(tick_marks)
    plt.ylabel('Actual')
    plt.xlabel('Predicted')
    plt.title(title)
    plt.show()


  def wandlog(self, num_epoch, X, Y,X_val, Y_val):
    accuracy = self.accuracy_score(X, Y)
    loss_train = self.Loss(X, Y)
    loss_valid = self.Loss(X_val, Y_val)
    val_accuracy = self.accuracy_score(X_val, Y_val)
    wandb.log({'epoch': num_epoch,           
              'loss': loss_train,
              'accuracy': accuracy,
              'val_loss': loss_valid,
              'val_accuracy': val_accuracy})
    
    if num_epoch % 5== 0:
      accuracy = self.accuracy_score(X, Y)
      loss_train = self.Loss(X, Y)
      loss_valid = self.Loss(X_val, Y_val)
      val_accuracy = self.accuracy_score(X_val, Y_val)
      library = {'epoch': num_epoch,           
              'loss': loss_train,
              'accuracy': accuracy,
              'val_loss': loss_valid,
              'val_accuracy': val_accuracy}

      print('Epoch: {}, Train Loss: {}, Train Accuracy: {}, Val Loss: {}, Val Accuracy: {}'.format(library['epoch'], library['loss'], library['accuracy'], library['val_loss'], library['val_accuracy']))
      if num_epoch == self.epochs:
        print('Model trained successfully !')

# model = FFNN(X_train, Y_train,
#                   epochs = 2, 
#                   hidden_layer_count = 3,
#                   hidden_layers =  [64, 64, 64],
#                   learning_rate = 0.0001,
#                   batch_size = 32,
#                   activation='ReLU',
#                   weight_init='random',
#                   loss = 'cross_entropy',
#                   weight_decay = 0.0005)
# model.fit(X_train, Y_train, X_val, Y_val,algo= 'adam', a = 1, show_loss = True) 
# confusion_matrix = model.confusion_matrix(X_test, Y_test)
# model.confo_matrixplot(confusion_matrix)

# wandb.init(project = 'Question_4_Best_Model', entity = 'ed22s009')

# algos = ['GD','SGD', 'MiniBatch', 'Momentum', 'NAG', 'AdaGrad', 'RMSProp', 'Adam','Nadam']
# configuration = {
#     'learning_rate': 0.001,
#     'epochs': 2,
#     'hidden_layer_count': 3,
#     'size_hidden_layers': 128,
#     'optimizer': 'adam',
#     'batch_size': 128,
#     'activation': 'ReLU',
#     'weight_initializations': 'Xavier',
#     'weight_decay': 0,
#     'loss_function': 'cross_entropy',
#     'dataset': 'fashion_mnist'#, "mnist"
# }

# def train():
  
#   wandb.init(project ='confusion_matrix',config=configuration, magic=True,reinit = True)
#   wandb.run.name = '/batch_size/'+str(wandb.config.batch_size)+'/learning_rate/'+ str(wandb.config.learning_rate)+'/epochs/'+str(wandb.config.epochs)+ '/optimizer/'+str(wandb.config.optimizer)+ '/hidden_layer_count/'+str(wandb.config.hidden_layer_count)+'/size_hidden_layers/'+str(wandb.config.size_hidden_layers)+ '/activation/'+str(wandb.config.activation)+'/weight_decay/'+str(wandb.config.weight_decay)+'/weight_initializations/'+str(wandb.config.weight_initializations)+'/loss_function/'+str(wandb.config.loss_function)

  
#   # [configuration['size_hidden_layers']] * configuration['hidden_layer_count']
  
#   hidden_layer_count = wandb.config.hidden_layer_count 
#   size_hidden_layers = wandb.config.size_hidden_layers 
#   model = FFNN(X_train, Y_train,
#                 epochs = wandb.config.epochs, 
#                 hidden_layer_count =  wandb.config.hidden_layer_count,
#                 hidden_layers = [size_hidden_layers]*hidden_layer_count,
#                 learning_rate = wandb.config.learning_rate,
#                 batch_size = wandb.config.batch_size,
#                 activation=wandb.config.activation,
#                 weight_init=wandb.config.weight_initializations,
#                 loss = wandb.config.loss_function,
#                 weight_decay = wandb.config.weight_decay)

#   algos = ['GD','SGD', 'MiniBatch', 'Momentum', 'NAG', 'AdaGrad', 'RMSProp', 'Adam','Nadam']
#   ["sgd", "momentum", "nag", "rmsprop", "adam", "nadam"]
#   ['momentum','sgd','rmsprop','nesterov','adam','nadam']
#   optimizer = wandb.config.optimizer
#   if optimizer == 'sgd':
#     weights = model.fit(X_train, Y_train, X_val, Y_val, algo= 'sgd')
#   elif optimizer == 'momentum':
#     weights =model.fit(X_train, Y_train, X_val, Y_val, algo= 'momentum')
#   elif optimizer == 'nag':
#     weights =model.fit(X_train, Y_train, X_val, Y_val, algo= 'nag')
#   elif optimizer == 'rmsprop':
#     weights =model.fit(X_train, Y_train, X_val, Y_val, algo= 'rmsprop')
#   elif optimizer == 'adam':
#     weights =model.fit(X_train, Y_train, X_val, Y_val, algo='adam')
#   elif optimizer =='nadam':
#     weights =model.fit(X_train, Y_train, X_val, Y_val, algo= 'nadam')
#   else:
#     print('Invalid optimizer')



#   confusion_matrix = model.confusion_matrix(X_test, Y_test)
#   print(confusion_matrix)
#   model.confo_matrixplot(confusion_matrix)

# if __name__ == '__main__':
#   train()
#   wandb.finish()

import argparse
wandb.init(project = 'Train_py', entity = 'ed22s009')


# algos = ['GD','SGD', 'MiniBatch', 'Momentum', 'NAG', 'AdaGrad', 'RMSProp', 'Adam','Nadam']
configuration = {
    'learning_rate': 0.001,
    'epochs': 2,
    'hidden_layer_count': 3,
    'size_hidden_layers': 128,
    'optimizer': 'adam',
    'batch_size': 128,
    'activation': 'ReLU',
    'weight_initializations': 'Xavier',
    'weight_decay': 0,
    'loss_function': 'cross_entropy',
    'dataset': 'fashion_mnist'
    }

def train(args):


  wandb.init(project ='Train_py',config=configuration, magic=True,reinit = True)
  wandb.run.name = '/batch_size/'+str(wandb.config.batch_size)+'/learning_rate/'+ str(wandb.config.learning_rate)+'/epochs/'+str(wandb.config.epochs)+ '/optimizer/'+str(wandb.config.optimizer)+ '/hidden_layer_count/'+str(wandb.config.hidden_layer_count)+'/size_hidden_layers/'+str(wandb.config.size_hidden_layers)+ '/activation/'+str(wandb.config.activation)+'/weight_decay/'+str(wandb.config.weight_decay)+'/weight_initializations/'+str(wandb.config.weight_initializations)+'/loss_function/'+str(wandb.config.loss_function)
  print("epochs=", args.epochs)
  print("hidden_layer_count=", args.hidden_layer_count)
  print("hidden_layers=", [args.size_hidden_layers] * args.hidden_layer_count)
  print("learning_rate=", args.learning_rate)
  print("batch_size=", args.batch_size)
  print("activation=", args.activation)
  print("weight_init=", args.weight_initializations)
  print("weight_decay=", args.weight_decay)
  print("optimizer=",args.optimizer )
  print('dataset=', args.dataset)
  
  # [configuration['size_hidden_layers']] * configuration['hidden_layer_count']

  # hidden_layer_count = wandb.config.hidden_layer_count 
  # size_hidden_layers = wandb.config.size_hidden_layers 
  X_train, X_val, X_test, Y_train, Y_val, Y_test = dataset_type(dataset = args.dataset)
  model = FFNN(X_train, Y_train,
                epochs=args.epochs, 
                hidden_layer_count=args.hidden_layer_count,
                hidden_layers=[args.size_hidden_layers] * args.hidden_layer_count,
                learning_rate=args.learning_rate,
                batch_size=args.batch_size,
                activation=args.activation,
                weight_init=args.weight_initializations,
                loss=wandb.config.loss_function,
                weight_decay=args.weight_decay)

  optimizer = args.optimizer

  algos = ['GD','SGD', 'MiniBatch', 'Momentum', 'NAG', 'AdaGrad', 'RMSProp', 'Adam','Nadam']
  ["sgd", "momentum", "nag", "rmsprop", "adam", "nadam"]
  ['momentum','sgd','rmsprop','nesterov','adam','nadam']
  if optimizer == 'sgd':
    weights = model.fit(X_train, Y_train, X_val, Y_val, algo= 'sgd')
  elif optimizer == 'momentum':
    weights =model.fit(X_train, Y_train, X_val, Y_val, algo= 'momentum')
  elif optimizer == 'nag':
    weights =model.fit(X_train, Y_train, X_val, Y_val, algo= 'nag')
  elif optimizer == 'rmsprop':
    weights =model.fit(X_train, Y_train, X_val, Y_val, algo= 'rmsprop')
  elif optimizer == 'adam':
    weights =model.fit(X_train, Y_train, X_val, Y_val, algo='adam')
  elif optimizer =='nadam':
    weights =model.fit(X_train, Y_train, X_val, Y_val, algo= 'nadam')
  else:
    print('Invalid optimizer')


  confusion_matrix = model.confusion_matrix(X_test, Y_test)
  print(confusion_matrix)
  model.confo_matrixplot(confusion_matrix)
  print(model.accuracy_score(X_test, Y_test))

if __name__ == '__main__':
  
  parser = argparse.ArgumentParser()
  parser.add_argument("-wp", "--wandb_project", default="myprojectname")
  parser.add_argument("-we", "--wandb_entity", default="ed22s009")
  parser.add_argument("-d", "--dataset", default="fashion_mnist", choices=["fashion_mnist","mnist" ])
  parser.add_argument("-e", "--epochs", default=10, type=int)
  parser.add_argument("-b", "--batch_size", default=128, type=int)
  parser.add_argument("-l", "--loss", default="cross_entropy", choices=["cross_entropy", "mean_squared_error"])
  parser.add_argument("-o", "--optimizer", default="adam", choices=["sgd", "momentum", "nag", "rmsprop", "adam", "nadam"])
  parser.add_argument("-lr", "--learning_rate", default=0.001, type=float)
  parser.add_argument("-w_d", "--weight_decay", default=0, type=float)
  parser.add_argument("-w_i", "--weight_initializations", default="Xavier", choices=["random", "Xavier"])
  parser.add_argument("-nhl", "--hidden_layer_count", default=3, type=int)
  parser.add_argument("-sz", "--size_hidden_layers", default=128, type=int)
  parser.add_argument("-a", "--activation", default="ReLU", choices=["ReLU", "sigmoid", "tanh"])

  args = parser.parse_args()

  train(args)
  wandb.finish()

# algos = ["sgd", "momentum", "nag", "rmsprop", "adam", "nadam"]
# init_method = ['random', 'Xavier']
# loss = ['cross_entropy', 'mean_squared_error']
# activation = ['sigmoid', 'tanh', 'ReLU']
# dataset  = ["fashion_mnist","mnist" ]
# !python train_7.py -wp Train_py -we ed22s009 -d mnist -e 20 -b 128 -lr 0.001 -nhl 3 -sz 128 -a ReLU -w_i Xavier -w_d 0 -o adam -l cross_entropy
