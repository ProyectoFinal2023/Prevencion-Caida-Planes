import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.feature_selection import SelectKBest, f_classif
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, confusion_matrix
import pickle

df = pd.read_csv('input_modelo_ml.csv')
df['contactar'] = df['contactar'].map({'SI': 1, 'NO': 0})

X = df[['cuotas_impagas', 'cuotas_pagas', 'cuotas_a_vencer', 'dias_atraso', 'situacion', 'riesgo', 'monto_deuda']]
y = df['contactar']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('selector', SelectKBest(score_func=f_classif, k='all')),
    ('classifier', LogisticRegression())
])

param_grid = {
    'selector__k': [3, 5, 'all'],
    'classifier__C': np.logspace(-4, 4, 20),
    'classifier__solver': ['lbfgs', 'liblinear']
}

grid_search = GridSearchCV(pipeline, param_grid, cv=5, scoring='accuracy', n_jobs=-1)
grid_search.fit(X_train, y_train)

best_model = grid_search.best_estimator_

y_pred = best_model.predict(X_test)
print(classification_report(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))

with open('prediction_model.pkl', 'wb') as file:
    pickle.dump(best_model, file)
