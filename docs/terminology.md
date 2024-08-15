# Terminology and Definitions

## 1. Introduction

This document provides a glossary of terms used in the `django-tenant-options` documentation. It aims to clarify the terminology and definitions related to multi-tenant architecture, custom options, and related concepts.

## 2. Glossary

### 2.1. Tenant

A tenant is an entity that uses a multi-tenant application. In the context of `django-tenant-options`, a tenant is an organization, group, or individual that has its own set of custom options. Each tenant can customize the available options to meet its specific requirements.

> 🟩 Note
>
> `django-tenant-options` has no relation to or requirement for any specific tenant architecture or package, but it provides a framework for managing custom options within a multi-tenant application. The only requirement is that the application must have a model representing tenants.

### 2.2. Options

Options are settings or choices that can be configured within a multi-tenant application and used in user-facing forms. Options may be predefined by the application developer as default options or defined by tenants as custom options. Options can influence the behavior, appearance, or functionality of the application's forms.

Options can be categorized into two main types: Default Options and Custom Options. All Options models must inherit from the `AbstractOption` model provided by `django-tenant-options`.

#### 2.2.1. Default Options

Default options are predefined settings or choices provided by the application developer. These options serve as the baseline configuration for all tenants and can include mandatory options that must be used by all tenants, as well as optional choices that tenants can adopt or ignore.

#### 2.2.2. Custom Options

Custom options are additional settings or choices that tenants can define and configure within a multi-tenant application. These options allow tenants to tailor the selectable values in user-facing forms to better suit their needs.

### 2.3 Selections

Selections refer to the specific Options that tenants decide to use or activate for their user-facing forms. Tenants can choose from the available Default Options and Custom Options to create a unique set of Selections that will be presented to users in the application's forms.

Selections are stored in the database as model instances for models subclassed from `AbstractSelection`, which is provided by `django-tenant-options`. Each Selection is associated with a specific tenant and an Option, allowing the application to retrieve and apply the selected options when rendering forms.

The Selections model serves as a through model between the Tenant model and the Option model, allowing for a many-to-many relationship between tenants and their selected Options.
